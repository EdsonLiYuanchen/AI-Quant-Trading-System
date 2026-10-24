"""
资金驱动型调仓引擎（在 AutoTradingEngine 之上叠加）
=====================================================
把"预设金额"作为唯一输入，灵活改变持仓：

核心思路
  - 输入：capital（预设金额）+ stock_pool（股票池，可含 A 股自选）
  - 目标组合（target）：按 评分 / 均分 把 capital 拆成每只股票的目标持仓金额
  - 调仓（rebalance）：每轮把 当前持仓 向 目标组合 靠拢：
      * 单只仓位偏离目标 > rebalance_band_pct 才动手（降低换手）
      * 超配 → 卖出至目标；欠配 → 买入至目标
      * 股票池外的持仓：可选 清仓 / 保持
  - 灵活改变持仓：
      * 资金不足时自动降档（按可买手数取整 + 降目标金额）
      * 股票池变化时自动重分配
      * 支持"只加仓不加仓" / "只减仓" / "双向" 三种方向模式

本模块不新建线程，复用 AutoTradingEngine 的 信号队列 / 执行线程：
  把"调仓动作"翻译成 一批 BUY / SELL 信号塞进 signal_queue，
  由引擎既有的 _execute_signals 统一执行，保证风控 / 日志 / 交易时段
  判断与原有逻辑完全一致。
"""

import time
import threading
import random

from auto_trading_engine import TradingSignal


# 调仓方向
DIRECTION_BOTH = 'both'        # 双向：可买可卖
DIRECTION_BUY_ONLY = 'buy'     # 只加仓（不动已有仓位）
DIRECTION_SELL_ONLY = 'sell'   # 只减仓 / 清仓



# ── 小白友好的辅助函数 ──────────────────────────────────────────────────────────
def min_lot_cost(price):
    """买 1 手（100 股）需要的金额（元）。价格无效返回 0。"""
    try:
        p = float(price or 0)
        return round(p * 100, 2) if p > 0 else 0
    except (TypeError, ValueError):
        return 0


def budget_hint(total, prices_dict=None):
    """根据总预算和价格字典，给出友好提示文字。

    返回 dict:
      - can_buy: 可买的股票只数估算
      - min_needed: 买 1 手最便宜股票需要的金额
      - msg: 友好提示文字
    """
    total = float(total or 0)
    if total <= 0:
        return {'can_buy': 0, 'min_needed': 0, 'msg': '请输入有效金额'}
    if not prices_dict:
        cheap = 200  # 默认最低 1 手成本
    else:
        costs = [min_lot_cost(p) for p in prices_dict.values() if p and float(p) > 0]
        cheap = min(costs) if costs else 200
    n_lots = max(0, int(total / cheap)) if cheap > 0 else 0
    if n_lots == 0:
        msg = '预算 %d 元，不足以买任何股票（最便宜 1 手约 %.0f 元）。建议至少 %.0f 元以上。' % (total, cheap, cheap * 2)
    elif n_lots <= 2:
        msg = '预算 %d 元，大约能买 %d 只股票（每只 1 手起）。点「智能选股」查看具体推荐。' % (total, n_lots)
    else:
        msg = '预算 %d 元充裕，可分散买约 %d 只股票。点击「智能选股」开始自动挑选。' % (total, n_lots)
    return {'can_buy': n_lots, 'min_needed': cheap, 'msg': msg}

class PresetCapitalAllocator:
    """把预设金额拆成目标组合"""

    def __init__(self, capital=0.0, stock_pool=None,
                 strategy='equal', weights=None,
                 target_total_ratio=0.9, keep_cash_ratio=0.1):
        self.capital = float(capital or 0.0)
        self.stock_pool = [str(c).strip() for c in (stock_pool or []) if str(c).strip()]
        # strategy: 'equal' 均分 / 'score' 按 AI 评分加权 / 'weights' 自定义
        self.strategy = strategy
        self.weights = weights or {}
        self.target_total_ratio = target_total_ratio
        self.keep_cash_ratio = keep_cash_ratio

    def set_capital(self, capital):
        self.capital = float(capital or 0.0)

    def set_stock_pool(self, pool):
        self.stock_pool = [str(c).strip() for c in (pool or []) if str(c).strip()]

    def allocate(self, scores=None):
        """把预设金额拆成目标组合：{代码: 目标金额(元)}。
        scores: 可选，{code: 0-100分}，strategy='score' 时用分数加权。
        若实例属性 _last_targets 已注入（动态调仓器按实时分数算好），直接返回它。
        """
        last = getattr(self, '_last_targets', None)
        if last is not None:
            out = last
            self._last_targets = None  # 一次性
            return out
        if not self.stock_pool or self.capital <= 0:
            return {}
        investable = self.capital * max(0.0, min(1.0, self.target_total_ratio))
        n = len(self.stock_pool)
        alloc = {}

        if self.strategy == 'weights' and self.weights:
            total_w = sum(float(self.weights.get(c, 0)) for c in self.stock_pool)
            for c in self.stock_pool:
                w = float(self.weights.get(c, 0)) / total_w if total_w > 0 else 0
                alloc[c] = investable * w
        elif self.strategy == 'score' and scores:
            weights = {c: max(0.0, float((scores or {}).get(c, 0) or 0)) for c in self.stock_pool}
            total_w = sum(weights.values())
            if total_w <= 0:
                # 没有有效评分 → 退化为均分
                alloc = {c: investable / n for c in self.stock_pool}
            else:
                alloc = {c: investable * (weights[c] / total_w) for c in self.stock_pool}
        else:
            # 均分
            alloc = {c: investable / n for c in self.stock_pool}

        # 按 1 手（100 股）取整到"目标金额"层面，保留小数；实际手数在引擎执行
        return {c: round(v, 2) for c, v in alloc.items() if v > 0}


class CapitalRebalancer:
    """资金驱动调仓器：把目标组合翻译成 BUY/SELL 信号"""

    def __init__(self, engine, allocator=None,
                 rebalance_band_pct=0.05,
                 direction=DIRECTION_BOTH,
                 handle_out_of_pool='keep',
                 min_trade_amount=200.0,
                 dry_run=False,
                 log=None):
        """
        :param engine: AutoTradingEngine 实例（复用其 trading_api / signal_queue / _log）
        :param allocator: PresetCapitalAllocator
        :param rebalance_band_pct: 偏离目标多少比例才调仓（默认 5%），降低换手
        :param direction: 'both' / 'buy' / 'sell'
        :param handle_out_of_pool: 池外持仓 'keep' 保持 / 'clear' 清仓
        :param min_trade_amount: 单只最小调仓金额（低于则不动，避免零钱抖动）
        :param dry_run: True 只记录计划、不下单
        :param log: 自定义日志函数，默认用 engine._log
        """
        self.engine = engine
        self.api = engine.trading_api
        self.allocator = allocator or PresetCapitalAllocator()
        self.rebalance_band_pct = max(0.0, float(rebalance_band_pct))
        self.direction = direction
        self.handle_out_of_pool = handle_out_of_pool
        self.min_trade_amount = float(min_trade_amount)
        self.dry_run = dry_run
        self._log = log or engine._log

        # 最近一次计划 / 执行结果（供 UI 展示）
        self.last_plan = None
        self.last_run_at = None

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------
    def _get_prices(self, codes):
        """{code: {'price':x, 'pct':x, 'volume':x, 'change':x}}。
        保留涨跌幅/量等字段，动态选股打分器可用。"""
        out = {}
        for c in codes:
            try:
                p = self.api.get_real_time_price(c) or {}
                price = float(p.get('price') or 0)
                out[c] = {
                    'price': price,
                    'pct': float(p.get('change_percent') or p.get('pct') or 0),
                    'change': float(p.get('change_amount') or p.get('change') or 0),
                    'volume': float(p.get('volume') or 0),
                }
            except Exception:
                out[c] = {'price': 0.0, 'pct': 0.0, 'change': 0.0, 'volume': 0.0}
        return out

    def _current_values(self):
        """当前持仓市值 {code: value}（含池外）"""
        vals = {}
        try:
            for p in self.api.get_positions():
                code = p.get('stock_code')
                vals[code] = float(p.get('current_value') or 0)
        except Exception:
            pass
        return vals

    def _account(self):
        try:
            return self.api.get_account_balance() or {}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # 生成调仓计划（纯计算，不下单）
    # ------------------------------------------------------------------
    def build_plan(self, scores=None):
        """返回 调仓计划：
        {
          'targets': {code: target_amount},
          'actions': [ {'code','side','target_amount','delta_amount','volume','reason'} ],
          'out_of_pool': {code: value},
          'total_target': x, 'current_total': y,
        }
        """
        alloc = self.allocator.allocate(scores)
        targets = alloc or {}
        cur = self._current_values()
        prices = self._get_prices(set(targets) | set(cur))
        acc = self._account()
        total_assets = float(acc.get('total_assets') or self.allocator.capital or 0)

        actions = []
        out_of_pool = {c: v for c, v in cur.items() if c not in targets}

        # 1) 池外持仓处理
        if self.handle_out_of_pool == 'clear' and self.direction in (DIRECTION_BOTH, DIRECTION_SELL_ONLY):
            for c, v in out_of_pool.items():
                vol = self._value_to_volume(v, self._price_of(prices, c))
                if vol > 0:
                    actions.append({'code': c, 'side': 'SELL', 'target_amount': 0.0,
                                    'delta_amount': -v, 'volume': vol,
                                    'reason': '池外持仓，清仓'})

        # 2) 按目标与当前差额调仓
        for c, tgt in targets.items():
            cur_v = cur.get(c, 0.0)
            delta = tgt - cur_v
            price = self._price_of(prices, c)

            if self.direction == DIRECTION_BUY_ONLY:
                # 只加仓：不动已有，仅把差额补到目标
                if delta > 0:
                    delta = min(delta, tgt - cur_v)
            elif self.direction == DIRECTION_SELL_ONLY:
                # 只减仓：只卖到目标，不买
                delta = min(delta, 0)
            # both：原样

            # 偏离 < 带宽 → 不动
            base = max(tgt, cur_v, 1e-9)
            if abs(delta) / base < self.rebalance_band_pct and self.direction != DIRECTION_SELL_ONLY:
                continue

            if delta > 0:
                side = 'BUY'
                if self.direction == DIRECTION_SELL_ONLY:
                    continue
                # 只允许买
            elif delta < 0:
                side = 'SELL'
                if self.direction == DIRECTION_BUY_ONLY:
                    continue
            else:
                continue

            vol = self._value_to_volume(abs(delta), price)
            if vol <= 0:
                continue
            amt = abs(delta)
            if amt < self.min_trade_amount:
                continue

            actions.append({'code': c, 'side': side, 'target_amount': tgt,
                            'delta_amount': delta, 'volume': vol,
                            'reason': f"目标 {tgt:.0f}，当前 {cur_v:.0f}"})

        plan = {
            'targets': targets,
            'actions': actions,
            'out_of_pool': out_of_pool,
            'total_target': sum(targets.values()),
            'current_total': sum(v for c, v in cur.items() if c in targets),
            'total_assets': total_assets,
        }
        self.last_plan = plan
        return plan

    @staticmethod
    def _price_of(prices, code):
        """prices 兼容 dict-of-dict 与 dict-of-float 两种结构。"""
        v = prices.get(code)
        if isinstance(v, dict):
            try:
                return float(v.get('price') or 0)
            except Exception:
                return 0.0
        try:
            return float(v or 0)
        except Exception:
            return 0.0

    def _value_to_volume(self, amount_yuan, price):
        """金额(元) → 手数（1 手=100 股），向下取整，价格无效返回 0。"""
        if price <= 0 or amount_yuan <= 0:
            return 0
        return int(amount_yuan / (price * 100))

    def get_min_budget(self, prices):
        """返回：要买得起所有候选股票各 1 手，最少需要多少元。
        prices: {code: price}。若为空返回 0。"""
        if not prices:
            return 0
        costs = [p * 100 for p in prices.values() if p and float(p) > 0]
        return max(costs) if costs else 0

    # ------------------------------------------------------------------
    # 执行调仓（翻译成 信号 塞进引擎队列）
    # ------------------------------------------------------------------
    def run_rebalance(self, scores=None, apply=True):
        """生成并（可选）执行一轮调仓。返回计划 + 执行摘要。"""
        plan = self.build_plan(scores)
        self.last_run_at = time.time()
        n_actions = len(plan['actions'])
        self._log(f"[调仓] 预设资金 {self.allocator.capital:.0f}，目标仓 {plan['total_target']:.0f}，"
                  f"当前仓 {plan['current_total']:.0f}，生成 {n_actions} 笔调仓"
                  + ("（dry_run，不下单）" if not apply or self.dry_run else ""))
        if not apply or self.dry_run:
            for a in plan['actions']:
                self._log(f"  [计划] {a['side']} {a['code']} {a['volume']}手 "
                          f"({a['delta_amount']:+.0f}元) {a['reason']}")
            return plan

        executed = 0
        for a in plan['actions']:
            conf = 0.95
            reason = a['reason']
            sig = TradingSignal(
                stock_code=a['code'],
                signal_type=a['side'],
                confidence=conf,
                reason='资金驱动调仓: ' + reason,
            )
            self.engine.signal_queue.put(sig)
            executed += 1
            self._log(f"  [入队] {a['side']} {a['code']} {a['volume']}手 @ 目标 {a['target_amount']:.0f}")

        plan['queued_actions'] = executed
        return plan

    # ------------------------------------------------------------------
    # 定时调仓（后台线程，复用引擎生命周期）
    # ------------------------------------------------------------------
    def start_loop(self, interval_sec=300, stop_event=None, scores_provider=None):
        """每 interval_sec 秒调仓一次。scores_provider 可返回 {code:score}。"""
        def loop():
            while (stop_event is None or not stop_event.is_set()) and self.engine.running:
                if self.engine.paused:
                    time.sleep(1)
                    continue
                try:
                    scores = scores_provider() if scores_provider else None
                    self.run_rebalance(scores=scores, apply=True)
                except Exception as e:
                    self._log(f"[调仓] 异常: {e}", 'ERROR')
                if stop_event is None:
                    time.sleep(interval_sec)
                else:
                    stop_event.wait(interval_sec)
        t = threading.Thread(target=loop, daemon=True)
        t.start()
        return t


# ----------------------------------------------------------------------
# 便捷构造：直接挂到 AutoTradingEngine 上
# ----------------------------------------------------------------------
def attach_capital_rebalancer(engine, capital, stock_pool,
                              strategy='equal', weights=None,
                              rebalance_band_pct=0.05,
                              direction=DIRECTION_BOTH,
                              handle_out_of_pool='keep',
                              min_trade_amount=200.0,
                              dry_run=False,
                              target_total_ratio=0.9):
    """给引擎挂一个 资金驱动调仓器，返回 CapitalRebalancer。"""
    alloc = PresetCapitalAllocator(capital=capital, stock_pool=stock_pool,
                                   strategy=strategy, weights=weights,
                                   target_total_ratio=target_total_ratio)
    reb = CapitalRebalancer(engine, allocator=alloc,
                           rebalance_band_pct=rebalance_band_pct,
                           direction=direction,
                           handle_out_of_pool=handle_out_of_pool,
                           min_trade_amount=min_trade_amount,
                           dry_run=dry_run)
    engine.capital_rebalancer = reb
    return reb
