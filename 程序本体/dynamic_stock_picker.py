# -*- coding: utf-8 -*-
"""
动态选股 + 资金驱动调仓（资金先行，实时盘面驱动换仓）
========================================================
设计目标（与"固定股票池"相反）：
  用户只给一笔金额 + 一个股票池(可选，做候选范围)。
  系统【实时】给池内(或全市场)股票打分，按分数动态决定：
    * 买什么：分数排名靠前的才给目标仓位
    * 买多少：仓位 ∝ 分数（高分多配、低分少配甚至清仓）
    * 换仓时机：盘面每变一次，目标组合就重算一次；
      分数下跌 → 自动减仓/清仓，分数上升 → 加仓，
      排名被别的股票超过 → 把仓位让给更强的。

  不预先锁死"买哪只"，持仓随盘面实时重排。

本模块复用 auto_trading_engine 的信号队列 / 执行线程，
把"调仓动作"翻译成 BUY/SELL 信号，由引擎统一执行（风控/T+1/日志一致）。
"""

import time
import threading

from auto_trading_engine import TradingSignal
from capital_rebalancer import CapitalRebalancer, PresetCapitalAllocator, DIRECTION_BOTH


# ----------------------------------------------------------------------------
# 实时评分器（打分器接口 + 几个内建打分器）
# ----------------------------------------------------------------------------
class Scorer:
    """打分器接口：score(pool, prices, positions) -> {code: 0~100}"""

    name = 'base'

    def score(self, pool, prices, positions):
        raise NotImplementedError


class MomentumScorer(Scorer):
    """动量 / 热度打分：用实时涨跌幅 + 成交量做一个 0~100 分。
    适合"实时关注盘面"：涨得强、放量的给高分，跌的给低分。
    prices: {code: {'price':x,'pct':x,'volume':x}}
    positions: {code: {'current_value':x}} 可选，用于避免已重仓的继续加分。
    """

    name = 'momentum'

    def __init__(self, top_ratio=0.5, volume_boost=0.2):
        self.top_ratio = top_ratio          # 前 50% 给分区间
        self.volume_boost = volume_boost    # 放量加分权重

    def score(self, pool, prices, positions=None):
        positions = positions or {}
        # 1) 按 实时涨幅 排名
        rows = []
        for c in pool:
            p = prices.get(c) or {}
            pct = float(p.get('pct') or 0)
            rows.append((c, pct))
        rows.sort(key=lambda x: -x[1])
        n = len(rows)
        out = {}
        for i, (c, pct) in enumerate(rows):
            # 排名分：第 1 名 100，垫底 0
            rank_score = 100.0 * (1 - i / max(1, n - 1))
            # 放量加分（有成交量字段时）
            vol_bonus = self.volume_boost * 100 if (prices.get(c) or {}).get('volume') else 0
            s = rank_score * (1 - self.volume_boost) + vol_bonus
            # 已重仓的略降分，避免越买越集中
            pos_val = positions.get(c, {}).get('current_value', 0)
            if pos_val > 0 and i >= n * 0.6:
                s *= 0.8
            out[c] = round(min(100.0, max(0.0, s)), 1)
        return out


class ValueMomentumScorer(MomentumScorer):
    """动量 + 低波动（预留接口，可结合 AI 评分 / 财报信息差进一步加权）"""
    name = 'value_momentum'


def make_scorer(kind='momentum'):
    if kind in ('score', 'ai', 'value_momentum'):
        # 这些走"按 AI / 外部评分加权"，由调用方提供 scores 时优先
        return ValueMomentumScorer()
    return MomentumScorer()


# ----------------------------------------------------------------------------
# 资金 → 分数 的 仓位分配（动态目标组合）
# ----------------------------------------------------------------------------
def allocate_by_score(capital, scores, target_total_ratio=0.9,
                      min_score=0.0, top_k=0, per_stock_cap_ratio=0.3):
    """按分数把 capital 拆成 {code: target_amount}。

    - 只给 score > min_score 的股票分配仓位
    - top_k>0 时只取分数前 top_k 只
    - per_stock_cap_ratio：单只最多占总资金比例（防过度集中）
    - 仓位 ∝ 分数（归一化到可投资金）
    """
    if not scores or capital <= 0:
        return {}
    investable = capital * max(0.0, min(1.0, target_total_ratio))

    items = [(c, float(s)) for c, s in scores.items() if float(s) > min_score]
    items.sort(key=lambda x: -x[1])
    if top_k and top_k > 0:
        items = items[:int(top_k)]
    total_score = sum(s for _, s in items)
    cap_amt = capital * max(0.0, min(0.99, float(per_stock_cap_ratio)))

    alloc = {}
    for c, s in items:
        amt = investable * (s / total_score) if total_score > 0 else investable / len(items)
        amt = min(amt, cap_amt)  # 单只上限
        if amt > 0:
            alloc[c] = round(amt, 2)
    return alloc


# ----------------------------------------------------------------------------
# 动态调仓器：资金先行 + 实时盘面 → 目标组合 → 买卖到目标
# ----------------------------------------------------------------------------
class DynamicCapitalRebalancer(CapitalRebalancer):
    """继承 CapitalRebalancer，但 targets 不再来自固定池，
    而是由 scorer 实时打分 + allocate_by_score 算出。"""

    def __init__(self, engine, capital=0.0, pool=None,
                 scorer=None, strategy_kind='momentum',
                 target_total_ratio=0.9, per_stock_cap_ratio=0.3,
                 min_score=0.0, top_k=0,
                 rebalance_band_pct=0.05,
                 direction=DIRECTION_BOTH,
                 handle_out_of_pool='keep',
                 min_trade_amount=200.0,
                 dry_run=False,
                 log=None,
                 external_scores_provider=None):
        alloc = PresetCapitalAllocator(capital=capital, stock_pool=pool or [],
                                       strategy='score', target_total_ratio=target_total_ratio)
        super().__init__(engine, allocator=alloc,
                         rebalance_band_pct=rebalance_band_pct,
                         direction=direction,
                         handle_out_of_pool=handle_out_of_pool,
                         min_trade_amount=min_trade_amount,
                         dry_run=dry_run, log=log)
        self.capital = float(capital or 0)
        self.pool = [str(c).strip() for c in (pool or []) if str(c).strip()]
        self.scorer = scorer if isinstance(scorer, Scorer) else make_scorer(strategy_kind)
        self.strategy_kind = strategy_kind
        self.target_total_ratio = target_total_ratio
        self.per_stock_cap_ratio = per_stock_cap_ratio
        self.min_score = min_score
        self.top_k = top_k
        self._external_scores = external_scores_provider or None

    # ---- 动态更新 ----
    def set_capital(self, capital):
        self.capital = float(capital or 0)
        self.allocator.capital = self.capital

    def set_pool(self, pool):
        self.pool = [str(c).strip() for c in (pool or []) if str(c).strip()]
        self.allocator.set_stock_pool(self.pool)

    # ---- 核心：实时打分 → 目标组合 → 计划 ----
    def build_plan(self, scores=None):
        # 1) 先拿实时盘面（现价/涨幅/量）
        universe = self.pool if self.pool else []
        prices = self._get_prices(universe) if universe else {}

        # 2) 实时打分（外部 scores_provider 优先，比如接 AI / 财报信息差）
        pos = {c: {'current_value': v} for c, v in self._current_values().items()}
        if self._external_scores:
            try:
                scores = self._external_scores(universe, prices, pos)
            except Exception:
                scores = None
        if scores is None:
            scores = self.scorer.score(universe, prices, pos)

        # 3) 资金 → 目标组合（按分数）
        self.allocator.capital = self.capital
        self.allocator.set_stock_pool(universe or list(scores.keys()))
        targets = allocate_by_score(
            self.capital, scores,
            target_total_ratio=self.target_total_ratio,
            min_score=self.min_score,
            top_k=self.top_k,
            per_stock_cap_ratio=self.per_stock_cap_ratio,
        )
        # 用父类的差额逻辑把 targets 翻译成 BUY/SELL 信号
        self.allocator._last_targets = targets
        plan = super().build_plan(scores=scores)
        plan['scores'] = scores
        plan['targets'] = targets
        return plan

