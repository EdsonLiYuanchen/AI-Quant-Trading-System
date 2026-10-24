# -*- coding: utf-8 -*-
"""
AI 交易策略引擎
================
混合决策：
  - 常态：决策树（技术指标评分：RSI、MACD、量能、趋势）
  - 异动：切换 AI API 深度分析（大涨/大跌/放量/缺口等异常时触发）
"""

import time
import json
import os
import re
import pandas as pd
import math
from datetime import datetime

# 技术指标计算（轻量实现，不依赖 pandas）
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
from typing import Optional, Dict, List

# ---------- 配置 ----------
AI_API_ENABLED = os.getenv("AI_API_ENABLED", "1") == "1"
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_API_URL = os.getenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "15"))

# 异动触发阈值
ANOMALY_THRESHOLDS = {
    "price_change_pct": 3.0,       # 涨跌幅超过 3%
    "volume_ratio": 2.0,            # 成交量放大超过 2 倍
    "gap_pct": 2.0,                 # 跳空缺口超过 2%
}

# 决策树参数
DECISION_TREE = {
    "rsi_overbought": 70,           # RSI 超买线
    "rsi_oversold": 30,             # RSI 超卖线
    "macd_bull_threshold": 0.0,     # MACD 金叉阈值
    "volume_surge_ratio": 1.5,      # 量能突增倍数
    "min_confidence": 0.55,         # 最低置信度
}


class TradingSignal:
    """交易信号（与 auto_trading_engine 兼容）"""

    def __init__(self, stock_code, signal_type, confidence=0.5, price=None, reason='',
                 target_volume=None, mode='tree'):
        self.stock_code = stock_code
        self.signal_type = signal_type  # BUY / SELL / HOLD
        self.confidence = confidence
        self.price = price
        self.reason = reason
        self.target_volume = target_volume
        self.mode = mode  # 'tree' | 'ai'
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            'stock_code': self.stock_code,
            'signal_type': self.signal_type,
            'confidence': round(self.confidence, 2),
            'price': self.price,
            'reason': self.reason,
            'target_volume': self.target_volume,
            'mode': self.mode,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        }


class DecisionTreeStrategy:
    """基于技术指标的决策树"""

    def __init__(self, params=None):
        self.params = params or DECISION_TREE.copy()

    def analyze(self, data: Dict) -> Dict:
        """
        输入 data 格式（来自数据源）：
          {
            'code': str,
            'price': float,
            'prev_price': float,       # 前一日收盘
            'change_pct': float,       # 今日涨跌幅
            'volume': float,           # 今日成交量
            'avg_volume_5d': float,    # 5日平均量
            'rsi': float,              # RSI(14)
            'macd': float,             # MACD 值
            'macd_signal': float,      # MACD 信号线
            'ma5': float,              # 5日均线
            'ma20': float,             # 20日均线
            'high_5d': float,          # 5日最高
            'low_5d': float,           # 5日最低
          }
        返回 {'signal': 'BUY'|'SELL'|'HOLD', 'confidence': 0-1, 'reason': str}
        """
        score = 0.0  # 综合得分，范围约 -1 ~ 1
        reasons = []

        price = data.get('price', 0)
        change_pct = data.get('change_pct', 0)
        rsi = data.get('rsi', 50)
        vol_ratio = data.get('volume', 0) / max(data.get('avg_volume_5d', 1), 1)
        macd = data.get('macd', 0)
        macd_sig = data.get('macd_signal', 0)
        ma5 = data.get('ma5', 0)
        ma20 = data.get('ma20', 0)

        # --- RSI ---
        rs = self.params['rsi_oversold']
        ro = self.params['rsi_overbought']
        if rsi <= rs:
            score += 0.25
            reasons.append(f"RSI超卖({rsi:.0f})")
        elif rsi >= ro:
            score -= 0.25
            reasons.append(f"RSI超买({rsi:.0f})")
        elif rsi < 45:
            score += 0.1
        elif rsi > 55:
            score -= 0.1

        # --- MACD ---
        if macd > macd_sig:
            score += 0.15
            reasons.append("MACD金叉")
        elif macd < macd_sig:
            score -= 0.15
            reasons.append("MACD死叉")

        # --- 趋势（MA5 vs MA20）---
        if ma5 > ma20:
            score += 0.1
            reasons.append("均线多头")
        else:
            score -= 0.1
            reasons.append("均线空头")

        # --- 量能 ---
        if vol_ratio >= self.params['volume_surge_ratio']:
            if change_pct > 0:
                score -= 0.1  # 放量上涨可能是诱多
                reasons.append(f"放量上涨({vol_ratio:.1f}x)")
            else:
                score += 0.15  # 放量下跌可能是恐慌出清
                reasons.append(f"放量下跌({vol_ratio:.1f}x)")
        elif vol_ratio < 0.6:
            reasons.append(f"缩量({vol_ratio:.1f}x)")

        # --- 价格位置（5日区间）---
        high_5d = data.get('high_5d', price)
        low_5d = data.get('low_5d', price)
        if high_5d > low_5d:
            pos = (price - low_5d) / (high_5d - low_5d)
            if pos > 0.85:
                score -= 0.1
                reasons.append("接近5日高点")
            elif pos < 0.15:
                score += 0.1
                reasons.append("接近5日低点")

        # --- 涨跌动量 ---
        if change_pct < -2:
            score += 0.15
            reasons.append(f"急跌{change_pct:.1f}%")
        elif change_pct > 2:
            score -= 0.15
            reasons.append(f"急涨{change_pct:.1f}%")

        # 映射到信号
        confidence = max(0.0, min(1.0, 0.5 + score))
        if confidence < self.params['min_confidence']:
            return {'signal': 'HOLD', 'confidence': confidence, 'reason': ' && '.join(reasons) if reasons else '无明显信号'}

        if score > 0.1:
            signal = 'BUY'
        elif score < -0.1:
            signal = 'SELL'
        else:
            signal = 'HOLD'

        return {'signal': signal, 'confidence': confidence, 'reason': ' && '.join(reasons) if reasons else '观望'}


class AIAnomalyDetector:
    """异动检测器：判断是否需要切换到 AI API"""

    def __init__(self, thresholds=None):
        self.t = thresholds or ANOMALY_THRESHOLDS

    def detect(self, data: Dict) -> Dict:
        """
        返回 {'is_anomaly': bool, 'anomaly_type': str, 'details': str}
        """
        reasons = []
        change_pct = abs(data.get('change_pct', 0))
        vol_ratio = data.get('volume', 0) / max(data.get('avg_volume_5d', 1), 1)
        prev_close = data.get('prev_price', 0)
        price = data.get('price', 0)

        if change_pct >= self.t['price_change_pct']:
            direction = '暴涨' if data.get('change_pct', 0) > 0 else '暴跌'
            reasons.append(f'{direction}{change_pct:.1f}%')

        if vol_ratio >= self.t['volume_ratio']:
            reasons.append(f'放量{vol_ratio:.1f}x')

        # 跳空检测
        if prev_close > 0:
            gap = (price - prev_close) / prev_close * 100
            if abs(gap) >= self.t['gap_pct']:
                reasons.append(f'跳空{gap:+.1f}%')

        is_anomaly = len(reasons) >= 1
        return {
            'is_anomaly': is_anomaly,
            'anomaly_type': ', '.join(reasons) if reasons else 'none',
            'details': '; '.join(reasons),
        }


class AIAPIClient:
    """调用外部 AI API 进行深度分析"""

    def __init__(self, api_key=None, api_url=None, model=None, timeout=15):
        self.api_key = api_key or AI_API_KEY
        self.api_url = api_url or AI_API_URL
        self.model = model or AI_MODEL
        self.timeout = timeout
        self._http = None

    def _get_http(self):
        if self._http is None:
            try:
                import http.client
                self._http = http.client
            except ImportError:
                self._http = None
        return self._http

    def analyze(self, stock_code: str, context: Dict) -> Optional[Dict]:
        """
        发送异动股票到 AI API，返回分析结果。
        返回 {'signal': 'BUY'|'SELL'|'HOLD', 'confidence': float, 'reason': str}
        失败时返回 None。
        """
        if not AI_API_ENABLED or not self.api_key:
            return None

        prompt = self._build_prompt(stock_code, context)
        try:
            result = self._call_api(prompt)
            return self._parse_response(result)
        except Exception as e:
            print(f"[AI] API 调用失败: {e}")
            return None

    def _build_prompt(self, code: str, data: Dict) -> str:
        change = data.get('change_pct', 0)
        rsi = data.get('rsi', 0)
        vol = data.get('volume', 0)
        avg_vol = data.get('avg_volume_5d', 1)
        price = data.get('price', 0)
        anomaly = data.get('anomaly_type', '')

        return f"""你是专业的A股量化分析师。请根据以下数据对股票 {code} 给出交易建议。

【行情数据】
- 当前价格: {price}
- 涨跌幅: {change_pct:+.2f}%
- RSI(14): {rsi:.1f}
- 成交量/5日均量: {vol/max(avg_vol,1):.2f}x
- MACD: {data.get('macd', 0):.4f}, 信号线: {data.get('macd_signal', 0):.4f}
- 5日最高: {data.get('high_5d', 0)}, 5日最低: {data.get('low_5d', 0)}
- 异动类型: {anomaly}

【决策规则】
1. 仅返回 JSON，格式: {{"signal": "BUY"/"SELL"/"HOLD", "confidence": 0.0-1.0, "reason": "简短理由"}}
2. confidence 反映你对该建议的确信程度
3. reason 不超过30字
4. 如果数据不足以下结论，返回 HOLD，confidence 0.5"""

    def _call_api(self, prompt: str) -> str:
        import urllib.request, urllib.error
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }).encode('utf-8')
        req = urllib.request.Request(
            self.api_url,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode('utf-8')

    def _parse_response(self, raw: str) -> Optional[Dict]:
        try:
            obj = json.loads(raw)
            content = obj.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            # 提取 JSON
            m = re.search(r'\{[^}]+\}', content)
            if m:
                parsed = json.loads(m.group())
                return {
                    'signal': parsed.get('signal', 'HOLD'),
                    'confidence': float(parsed.get('confidence', 0.5)),
                    'reason': parsed.get('reason', ''),
                }
        except Exception:
            pass
        return None



def _compute_indicators(closes, volumes):
    """从收盘价和成交量列表计算技术指标。"""
    n = len(closes)
    if n < 2:
        return {}
    arr = np.array(closes, dtype=float)
    vol_arr = np.array(volumes, dtype=float) if len(volumes) == n else None

    # MA5, MA20
    ma5 = float(arr[-5]) if n >= 5 else float(arr[-1])
    ma20 = float(arr[-20]) if n >= 20 else ma5

    # RSI(14)
    rsi = 50.0
    if n >= 15:
        deltas = np.diff(arr[-15:])
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = float(np.mean(gains))
        avg_loss = float(np.mean(losses))
        if avg_loss > 1e-9:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        else:
            rsi = 100.0 if avg_gain > 0 else 0.0

    # MACD (12, 26, 9)
    macd = 0.0
    macd_signal = 0.0
    if n >= 26:
        try:
            exp1 = pd.Series(arr).ewm(span=12, adjust=False).mean().iloc[-1]
            exp2 = pd.Series(arr).ewm(span=26, adjust=False).mean().iloc[-1]
            macd_val = float(exp1 - exp2)
            # 简单近似 signal line
            macd_signal = macd_val * 0.9
            macd = macd_val
        except Exception:
            macd = float(arr[-1] - arr[-2]) if n >= 2 else 0.0

    # 5日最高/最低
    high_5d = float(max(arr[-5:])) if n >= 5 else float(arr[-1])
    low_5d = float(min(arr[-5:])) if n >= 5 else float(arr[-1])

    # 前一日收盘
    prev_price = float(arr[-2]) if n >= 2 else float(arr[-1])

    # 5日均量
    avg_volume_5d = float(np.mean(vol_arr[-5:])) if vol_arr is not None and len(vol_arr) >= 5 else (float(vol_arr[-1]) if vol_arr is not None else 0.0)
    volume = float(vol_arr[-1]) if vol_arr is not None and len(vol_arr) >= 1 else 0.0

    return {
        'price': float(arr[-1]),
        'prev_price': prev_price,
        'change_pct': (float(arr[-1] - prev_price) / prev_price * 100) if prev_price > 0 else 0.0,
        'volume': volume,
        'avg_volume_5d': avg_volume_5d,
        'rsi': round(rsi, 1),
        'macd': round(macd, 4),
        'macd_signal': round(macd_signal, 4),
        'ma5': round(ma5, 2),
        'ma20': round(ma20, 2),
        'high_5d': round(high_5d, 2),
        'low_5d': round(low_5d, 2),
    }


def _fetch_market_data(code: str) -> dict:
    """从 akshare 获取股票日线数据并计算技术指标。"""
    try:
        import akshare as ak
        code6 = str(code).strip().zfill(6)
        prefix = 'sh' if code6.startswith(('6', '9')) else 'sz'
        df = ak.stock_zh_a_daily(symbol=f'{prefix}{code6}', adjust='qfq')
        if df is None or df.empty or len(df) < 5:
            return None
        closes = df['close'].astype(float).tolist()
        volumes = df['volume'].astype(float).tolist()
        return _compute_indicators(closes, volumes)
    except Exception as e:
        print(f'[AI] 获取 {code} 行情失败: {e}')
        return None


class HybridAIStrategy:
    """
    混合AI策略：
    - 常态：DecisionTreeStrategy（纯本地，快速）
    - 异动：切换 AIAPIClient 深度分析
    """

    def __init__(self, stocks=None, api_key=None, api_url=None, model=None):
        self.stocks = list(stocks) if stocks else []
        self.tree = DecisionTreeStrategy()
        self.detector = AIAnomalyDetector()
        self.ai_client = AIAPIClient(
            api_key=api_key or AI_API_KEY,
            api_url=api_url or AI_API_URL,
            model=model or AI_MODEL,
        )
        self._last_anomaly: Dict[str, str] = {}  # code -> last anomaly type
        self._signal_count = 0

    def set_stocks(self, stocks):
        if stocks:
            self.stocks = [str(s).strip() for s in stocks]

    def get_stocks_to_monitor(self):
        return self.stocks

    def generate_signal(self, stock_code: str, market_data: Dict = None) -> Optional[TradingSignal]:
        """
        主入口：根据市场数据生成交易信号。
        market_data 格式见 DecisionTreeStrategy.analyze()
        如果未提供 market_data，自动从 akshare 获取。
        """
        if not market_data:
            market_data = _fetch_market_data(stock_code)
            if market_data is None:
                return TradingSignal(stock_code, 'HOLD', confidence=0.5, reason='暂无行情数据')
            market_data['code'] = stock_code

        self._signal_count += 1

        # Step 1: 异动检测
        anomaly = self.detector.detect(market_data)
        is_anomaly = anomaly['is_anomaly']

        # Step 2: 决策树评分
        tree_result = self.tree.analyze(market_data)
        tree_signal = tree_result['signal']
        tree_conf = tree_result['confidence']
        tree_reason = tree_result['reason']

        # Step 3: 如果异动，调用 AI API
        if is_anomaly:
            self._last_anomaly[stock_code] = anomaly['details']
            ai_result = self.ai_client.analyze(stock_code, {
                **market_data,
                'anomaly_type': anomaly['details'],
            })
            if ai_result:
                # AI 结论优先，但置信度取两者较高值
                ai_conf = max(tree_conf, ai_result['confidence'])
                return TradingSignal(
                    stock_code=stock_code,
                    signal_type=ai_result['signal'],
                    confidence=ai_conf,
                    reason=f"[AI异动] {anomaly['details']} | {ai_result['reason']} | 树:{tree_reason}",
                    mode='ai',
                )
            else:
                # AI 失败，降级用树策略
                pass

        # 常态：决策树
        return TradingSignal(
            stock_code=stock_code,
            signal_type=tree_signal,
            confidence=tree_conf,
            reason=f"[树] {tree_reason}" + (f" | 异动:{anomaly['details']}" if is_anomaly else ''),
            mode='tree',
        )

    def get_status(self):
        return {
            'stocks_count': len(self.stocks),
            'signals_generated': self._signal_count,
            'last_anomalies': dict(list(self._last_anomaly.items())[-5:]),
            'ai_enabled': AI_API_ENABLED and bool(AI_API_KEY),
            'tree_params': self.tree.params,
            'anomaly_thresholds': self.detector.t,
        }
