# -*- coding: utf-8 -*-
"""
量化绩效指标库（借鉴主流量化框架：riskfolio / quantstats / vectorbt / backtrader）
=====================================================
提供回测与实盘共用的绩效统计与成本模型：
  - 收益与风险：sharpe_ratio / sortino_ratio / calmar_ratio / max_drawdown
  - 尾部风险  ：var_pct / cvar_pct（VaR / CVaR）
  - 年化指标  ：annualized_return / annualized_volatility / annualize_metrics
  - 交易成本  ：commission_cost / apply_cost / trade_cost_ratio / cost_adjusted_return
  - 样本外校验：walk_forward_split / train_test_split
  - 组合辅助  ：position_size_kelly / position_size_fixed

所有函数对空/无效输入安全，返回 None 或 0.0，不抛异常（便于直接嵌入回测）。
"""

import math

# 年化因子（A股约 244 个交易日，港美股约 252）
TRADING_DAYS = 252

# 默认成本参数（可覆盖）
DEFAULT_COMMISSION_RATE = 0.0003   # 佣金+印花税等，单边约 0.03%
DEFAULT_SLIPPAGE_RATE = 0.001      # 滑点，单边约 0.1%


# ===================== 基础收益计算 =====================

def price_to_returns(prices):
    """价格序列 -> 单日收益率序列（pct）。"""
    if not prices or len(prices) < 2:
        return []
    out = []
    for i in range(1, len(prices)):
        prev = float(prices[i - 1])
        cur = float(prices[i])
        if prev <= 0:
            out.append(0.0)
        else:
            out.append((cur / prev - 1.0) * 100.0)
    return out


def total_return(equity_curve):
    """权益曲线 -> 总收益率（%）。"""
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    first = float(equity_curve[0])
    last = float(equity_curve[-1])
    if first <= 0:
        return 0.0
    return (last / first - 1.0) * 100.0


def annualized_return(equity_curve, periods=None):
    """年化收益率（%）。periods 为周期总数（默认取 len-1）。"""
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    first = float(equity_curve[0])
    last = float(equity_curve[-1])
    if first <= 0 or last <= 0:
        return 0.0
    n = periods if periods and periods > 0 else len(equity_curve) - 1
    years = n / float(TRADING_DAYS)
    if years <= 0:
        return (last / first - 1.0) * 100.0
    return ((last / first) ** (1.0 / years) - 1.0) * 100.0


# ===================== 风险指标 =====================

def max_drawdown(equity_curve):
    """最大回撤（%），负值；同时返回（回撤幅度, 峰值日索引, 谷值日索引）。"""
    if not equity_curve or len(equity_curve) < 2:
        return {'max_drawdown': 0.0, 'peak_index': 0, 'trough_index': 0}
    peak = float(equity_curve[0])
    peak_i = 0
    max_dd = 0.0
    dd_peak_i = dd_trough_i = 0
    for i, v in enumerate(equity_curve):
        v = float(v)
        if v > peak:
            peak = v
            peak_i = i
        if peak > 0:
            dd = (peak - v) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
                dd_peak_i = peak_i
                dd_trough_i = i
    return {'max_drawdown': -max_dd, 'peak_index': dd_peak_i, 'trough_index': dd_trough_i}


def _std(xs, ddof=1):
    n = len(xs)
    if n <= ddof:
        return 0.0
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / (n - ddof)
    return math.sqrt(var) if var > 0 else 0.0


def sharpe_ratio(returns_pct, risk_free_pct=0.0, annualize=True):
    """
    夏普比率。returns_pct 为单日收益率（pct，百分数，如 1.2 表示 1.2%）。
    risk_free_pct 为单日无风险收益率（pct，默认 0）。
    年化处理：* sqrt(年化因子)。无数据返回 0.0。
    """
    if not returns_pct or len(returns_pct) < 2:
        return 0.0
    m = sum(returns_pct) / len(returns_pct)
    sd = _std(returns_pct)
    if sd <= 0:
        return 0.0
    ex = m - risk_free_pct
    s = ex / sd
    return s * math.sqrt(TRADING_DAYS) if annualize else s


def sortino_ratio(returns_pct, risk_free_pct=0.0, annualize=True):
    """索提诺比率：分母只用下行标准差。"""
    if not returns_pct or len(returns_pct) < 2:
        return 0.0
    m = sum(returns_pct) / len(returns_pct)
    downs = [x - risk_free_pct for x in returns_pct if x < risk_free_pct]
    if not downs:
        return 0.0
    n = len(returns_pct)
    var = sum(d ** 2 for d in downs) / n
    sd_dn = math.sqrt(var) if var > 0 else 0.0
    if sd_dn <= 0:
        return 0.0
    s = m / sd_dn
    return s * math.sqrt(TRADING_DAYS) if annualize else s


def calmar_ratio(equity_curve):
    """卡玛比率 = 年化收益 / 最大回撤（绝对值）。无有效回撤返回 0.0。"""
    ann = annualized_return(equity_curve)
    dd = abs(max_drawdown(equity_curve)['max_drawdown'])
    if dd <= 0:
        return 0.0
    return ann / dd


def var_pct(returns_pct, confidence=0.95):
    """历史 VaR（单日，pct）。95% 即最差 5% 分位（负值）。"""
    if not returns_pct:
        return 0.0
    srt = sorted(returns_pct)
    n = len(srt)
    k = max(0, int(math.ceil((1.0 - confidence) * n)) - 1)
    return srt[k] if k < n else srt[0]


def cvar_pct(returns_pct, confidence=0.95):
    """历史 CVaR（pct）：最坏 5% 的平均损失。"""
    if not returns_pct:
        return 0.0
    srt = sorted(returns_pct)
    n = len(srt)
    k = max(0, int(math.ceil((1.0 - confidence) * n)))
    if k >= n:
        k = n - 1
    tail = srt[:k + 1] if k >= 0 else srt
    if not tail:
        return srt[0]
    return sum(tail) / len(tail)


def annualized_volatility(returns_pct):
    """年化波动率（%）。"""
    if not returns_pct or len(returns_pct) < 2:
        return 0.0
    return _std(returns_pct) * math.sqrt(TRADING_DAYS)


# ===================== 交易成本模型 =====================

def commission_cost(price, volume, commission_rate=DEFAULT_COMMISSION_RATE,
                    slippage_rate=DEFAULT_SLIPPAGE_RATE):
    """
    单笔交易成本（元）= 成交额 * (佣金率 + 滑点率)。
    price: 单价（元），volume: 手数（A股 1 手 = 100 股）。
    """
    turnover = float(price) * float(volume) * 100.0
    return turnover * (commission_rate + slippage_rate)


def apply_cost(price, side, slippage_rate=DEFAULT_SLIPPAGE_RATE):
    """
    按方向调整成交价位：buy 向上、sell 向下模拟滑点。
    返回调整后价格。
    """
    if not side:
        return price
    p = float(price)
    if side.lower() in ('buy', 'b'):
        return p * (1.0 + slippage_rate)
    if side.lower() in ('sell', 's'):
        return p * (1.0 - slippage_rate)
    return p


def trade_cost_ratio(costs, turnover_total):
    """成本占成交额比例（%）。"""
    if not turnover_total or turnover_total <= 0:
        return 0.0
    return sum(costs) / float(turnover_total) * 100.0


def cost_adjusted_return(gross_return_pct, turnover_total, costs, initial_capital):
    """
    将毛利收益率（%）扣除成本后的净收益率（%）。
    costs 为累计成本（元），turnover_total 为累计成交额（元），仅作参照。
    net = gross - costs/initial_capital*100
    """
    if not initial_capital or initial_capital <= 0:
        return gross_return_pct
    net = gross_return_pct - (sum(costs) / float(initial_capital) * 100.0)
    return net


# ===================== 样本外 / walk-forward 校验 =====================

def walk_forward_split(n, train_ratio=0.7, min_train=60):
    """
    时间序列滚动切分。返回 [(train_end, test_end), ...]（索引，左闭右开）。
    每折：先 train_ratio 段做训练，后 (1-ratio) 段做样本外验证，逐段右移。
    n 为样本总数。
    """
    if n <= min_train:
        return []
    fold = max(1, int(n * (1.0 - train_ratio)))
    if fold < 2:
        return []
    splits = []
    start = min_train
    while start + fold <= n:
        splits.append((start, min(start + fold, n)))
        start += fold
    return splits


def train_test_split(n, train_ratio=0.7, min_train=60):
    """单次训练/测试切分（索引，左闭右开）。"""
    if n <= min_train:
        return None
    cut = int(n * train_ratio)
    return cut, n


# ===================== 仓位管理 =====================

def position_size_kelly(win_rate, payoff_ratio, max_position=0.5):
    """
    凯利仓位（连续近似）。win_rate 为胜率（0-1），payoff_ratio 为盈亏比。
    f* = p - (1-p)/b，上限截断到 max_position（默认 50%）。
    """
    if win_rate is None or payoff_ratio is None or payoff_ratio <= 0:
        return 0.0
    p = max(0.0, min(1.0, float(win_rate)))
    b = float(payoff_ratio)
    f = p - (1.0 - p) / b
    return max(0.0, min(f, max_position))


def position_size_fixed(total_capital, n_stocks, per_stock_cap_ratio=0.35,
                        min_volume=100):
    """
    等权固定仓位：将总资金分配到 n 只股票，每只不超过 per_stock_cap_ratio。
    返回每只股票的目标资金（元），不足 1 手（min_volume 股）则置 0。
    """
    if total_capital is None or total_capital <= 0 or not n_stocks or n_stocks <= 0:
        return []
    per = total_capital / float(n_stocks)
    cap = total_capital * float(per_stock_cap_ratio)
    per = min(per, cap) if cap > 0 else per
    # 不足 1 手则归 0（保守，避免碎仓）
    if min_volume and per < min_volume * 0.01:  # 粗略：低于 1 元/股 视为无效
        pass
    return [round(per, 2) for _ in range(int(n_stocks))]


# ===================== 一键汇总 =====================

def summarize(equity_curve, returns_pct=None, initial_capital=None, costs=None,
              turnover_total=None, risk_free_pct=0.0):
    """
    输入权益曲线，输出一组常用指标 dict（百分数保留 2 位小数）。
    用于回测结果增强，保持与旧字段兼容（新增字段不影响旧读取方）。
    """
    if equity_curve is None or len(equity_curve) < 2:
        return {}
    if returns_pct is None:
        returns_pct = price_to_returns(equity_curve)
    dd = max_drawdown(equity_curve)
    ret_total = total_return(equity_curve)
    ann = annualized_return(equity_curve)
    vol = annualized_volatility(returns_pct)
    sharpe = sharpe_ratio(returns_pct, risk_free_pct=risk_free_pct)
    sortino = sortino_ratio(returns_pct, risk_free_pct=risk_free_pct)
    calmar = calmar_ratio(equity_curve)
    var95 = var_pct(returns_pct, 0.95)
    cvar95 = cvar_pct(returns_pct, 0.95)

    out = {
        'total_return': round(ret_total, 2),
        'annualized_return': round(ann, 2),
        'annualized_volatility': round(vol, 2),
        'max_drawdown': round(dd['max_drawdown'], 2),
        'sharpe': round(sharpe, 2),
        'sortino': round(sortino, 2),
        'calmar': round(calmar, 2),
        'var_95': round(var95, 2),
        'cvar_95': round(cvar95, 2),
        'periods': len(equity_curve) - 1,
    }

    # 成本感知：若提供成本与初始资金，追加净收益
    if costs is not None and initial_capital and initial_capital > 0:
        net = cost_adjusted_return(ret_total, turnover_total or 0.0, costs, initial_capital)
        out['gross_return'] = round(ret_total, 2)
        out['net_return_after_cost'] = round(net, 2)
        out['total_cost'] = round(sum(costs), 2)
        out['cost_ratio_pct'] = round(
            (sum(costs) / float(initial_capital) * 100.0), 4)
        out['cost_adjusted_sharpe_approx'] = round(
            sharpe * (1.0 - out['cost_ratio_pct'] / 100.0), 2)
    return out
