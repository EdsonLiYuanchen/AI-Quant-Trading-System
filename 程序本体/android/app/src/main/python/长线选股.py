"""
长线选股分析模块
综合历史行情走势 + 财务基本面 + AI模型预测，评估一只股票是否适合长期持有。
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

import time
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from 智能数据查询 import SmartDataClient
from 多模型AI量化交易 import AIStrategyOptimizer, AITradingStrategy

# 财务指标关键字
FUND_KEYWORDS = {
    'roe': '净资产收益率',
    'revenue_growth': '营业总收入增长率',
    'profit_growth': '归属母公司净利润增长率',
    'gross_margin': '毛利率',
    'debt_ratio': '资产负债率',
    'eps': '基本每股收益',
    'cash_to_profit': '经营活动净现金/归属母公司的净利润',
    'revenue': '营业总收入',
    'profit': '归母净利润',
}


def _to_float(v, default=0.0):
    try:
        v = float(v)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _call_with_timeout(fn, timeout):
    """
    在线程中调用 fn()，若超过 timeout 秒仍未返回则抛出 TimeoutError。
    用于把可能无限挂起的网络请求变成"快速失败"，避免整个刷新卡死。
    """
    box = {}

    def runner():
        try:
            box['v'] = fn()
        except Exception as e:
            box['e'] = e

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError(f"网络请求超时({timeout}s)")
    if 'e' in box:
        raise box['e']
    return box['v']


import sys as _sys


class _Null:
    """写不进任何地方的无害输出对象（打包后 sys.stdout 为 None 时的兜底）"""
    def write(self, s):
        pass

    def flush(self):
        pass


def _ak_call(fn, timeout):
    """
    带超时且防止 stdout/stderr 为 None 的 akshare 调用。
    打包版 console=False 时 sys.stdout=None，akshare 内部 tqdm 写 stdout 会崩，
    这里临时换成无害对象，调用完还原。
    """
    saved = (_sys.stdout, _sys.stderr)
    changed = False
    if _sys.stdout is None:
        _sys.stdout = _Null()
        changed = True
    if _sys.stderr is None:
        _sys.stderr = _Null()
        changed = True
    try:
        return _call_with_timeout(fn, timeout)
    finally:
        if changed:
            _sys.stdout, _sys.stderr = saved



class LongTermAnalyzer:
    """长线选股分析器"""

    def __init__(self, client=None, ai_model='2'):
        self.client = client or SmartDataClient()
        self.ai_model = ai_model  # 2=梯度提升树
        # 数据源健康标记：东财/财务源一旦确认连不上就跳过，避免每只股票重复白等超时
        self._em_history_down = False
        self._fin_down = False
        self._hist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_cache')
        self._fin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_cache')

    # ------------------------------------------------------------------
    # 交易时段判断
    # ------------------------------------------------------------------
    @staticmethod
    def is_trading_time(dt=None):
        """
        A股交易时段：工作日 9:15-11:30、13:00-15:00。
        盘中返回 True（实时榜单）；收盘/非交易日返回 False（当日总结）。
        """
        if dt is None:
            dt = datetime.now()
        if dt.weekday() >= 5:  # 周六周日
            return False
        hm = dt.hour * 60 + dt.minute
        return (555 <= hm <= 690) or (780 <= hm <= 900)

    # ------------------------------------------------------------------
    # 数据获取
    # ------------------------------------------------------------------
    def fetch_history(self, token, years=3):
        """获取历史日线数据（多数据源回退），返回规整中文列名的 DataFrame"""
        end = datetime.now()
        start = end - timedelta(days=int(years * 365))
        start_str = start.strftime('%Y%m%d')
        end_str = end.strftime('%Y%m%d')

        # 先解析代码
        code = None
        try:
            syms = self.client.resolve(token)
            if syms:
                s = syms[0]
                if s.type == 'stock':
                    code = s.code.zfill(6)
                    name = s.name
        except Exception:
            pass

        if not code:
            digits = ''.join(ch for ch in token if ch.isdigit())
            if len(digits) == 6:
                code = digits
                name = token
            else:
                return pd.DataFrame()

        # 磁盘缓存：同一天内不重复抓取 3 年日线，重复刷新直接秒开
        cache = os.path.join(self._hist_dir, 'hist_%s_%dy.csv' % (code, int(years)))
        try:
            if os.path.exists(cache) and (time.time() - os.path.getmtime(cache)) < 86400:
                return pd.read_csv(cache, dtype={'代码': str})
        except Exception:
            pass

        # 1) 东财（智能客户端）— 本机常连不上，确认一次后后续直接跳过
        if not self._em_history_down:
            try:
                df = _call_with_timeout(
                    lambda: self.client.get_history(code, start_date=start_str, end_date=end_str, adjust='qfq'),
                    timeout=5)
                if df is not None and not df.empty:
                    out = self._normalize(df, name)
                    self._save_hist_cache(cache, out)
                    return out
            except Exception:
                self._em_history_down = True  # 东财连不上，之后不再尝试
                pass

        # 2) 腾讯直连 fqkline（不依赖 akshare，最稳定，榜单深度分析首选）
        try:
            import requests
            prefix = 'sh' if code.startswith(('6', '9')) else 'sz'
            start_dash = start.strftime('%Y-%m-%d')
            end_dash = end.strftime('%Y-%m-%d')
            url = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
            headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://gu.qq.com/'}
            rows = []
            _end = end_dash
            for _ in range(6):
                r = requests.get(url, params={'param': '%s%s,day,%s,%s,2000,qfq' % (prefix, code, start_dash, _end)},
                                 headers=headers, timeout=10)
                node = (r.json().get('data') or {}).get('%s%s' % (prefix, code), {})
                kl = node.get('qfqday') or node.get('day') or []
                if not kl:
                    break
                rows = list(kl) + rows
                if kl[0][0] <= start_dash:
                    break
                # 腾讯单次最多返 640 根（尾部起），需把结束日期往前推继续补更早的数据
                try:
                    _end = (datetime.strptime(kl[0][0], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
                except Exception:
                    break
            seen = set()
            uniq = []
            for it in rows:
                if len(it) < 6 or it[0] in seen:
                    continue
                seen.add(it[0])
                uniq.append(it)
            if uniq:
                raw = pd.DataFrame({
                    '日期': [x[0] for x in uniq],
                    '开盘': [float(x[1]) for x in uniq],
                    '收盘': [float(x[2]) for x in uniq],
                    '最高': [float(x[3]) for x in uniq],
                    '最低': [float(x[4]) for x in uniq],
                    '成交量': [float(x[5]) for x in uniq],
                })
                raw['代码'] = code
                raw['名称'] = name if name else code
                raw['日期'] = pd.to_datetime(raw['日期']).dt.strftime('%Y-%m-%d')
                raw = raw[raw['日期'] >= start_dash]
                out = raw.reset_index(drop=True)
                self._save_hist_cache(cache, out)
                return out
        except Exception:
            pass

        # 3) 新浪
        try:
            import akshare as ak
            prefix = 'sh' if code.startswith(('6', '9')) else 'sz'
            raw = _ak_call(lambda: ak.stock_zh_a_daily(
                symbol=f"{prefix}{code}", start_date=start_str, end_date=end_str, adjust='qfq'), timeout=10)
            if raw is not None and not raw.empty:
                raw = raw.rename(columns={'date': '日期', 'open': '开盘', 'high': '最高',
                                          'low': '最低', 'close': '收盘', 'volume': '成交量',
                                          'amount': '成交额', 'turnover': '换手率'})
                raw['代码'] = code
                raw['名称'] = name if name else code
                raw['日期'] = pd.to_datetime(raw['日期']).dt.strftime('%Y-%m-%d')
                out = raw.reset_index(drop=True)
                self._save_hist_cache(cache, out)
                return out
        except Exception:
            pass

        # 3) 腾讯
        try:
            import akshare as ak
            prefix = 'sh' if code.startswith(('6', '9')) else 'sz'
            raw = _ak_call(lambda: ak.stock_zh_a_hist_tx(
                symbol=f"{prefix}{code}", start_date=start_str, end_date=end_str, adjust='qfq'), timeout=10)
            if raw is not None and not raw.empty:
                raw = raw.rename(columns={'date': '日期', 'open': '开盘', 'high': '最高',
                                          'low': '最低', 'close': '收盘', 'amount': '成交额'})
                raw['代码'] = code
                raw['名称'] = name if name else code
                raw['日期'] = pd.to_datetime(raw['日期']).dt.strftime('%Y-%m-%d')
                out = raw.reset_index(drop=True)
                self._save_hist_cache(cache, out)
                return out
        except Exception:
            pass

        return pd.DataFrame()

    def _save_hist_cache(self, cache, df):
        """保存历史日线到本地缓存（次日自动过期重抓）"""
        try:
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            df.to_csv(cache, index=False, encoding='utf-8-sig')
        except Exception:
            pass

    @staticmethod
    def _normalize(df, name=''):
        """将东财接口返回的中文列 DataFrame 规整为标准列"""
        if df is None or df.empty:
            return df
        out = df.copy()
        rename = {'日期': '日期', '开盘': '开盘', '收盘': '收盘', '最高': '最高',
                  '最低': '最低', '成交量': '成交量', '成交额': '成交额', '换手率': '换手率'}
        keep = {k for k in rename if k in out.columns}
        out = out[list(keep)].copy()
        out['日期'] = pd.to_datetime(out['日期']).dt.strftime('%Y-%m-%d')
        if '代码' not in out.columns:
            out['代码'] = name
        if '名称' not in out.columns:
            out['名称'] = name
        return out.reset_index(drop=True)

    def fetch_fundamentals(self, code):
        """获取财务基本面数据，返回指标字典（None 表示取不到）"""
        if self._fin_down:
            return {}
        cache = os.path.join(self._fin_dir, 'fund_%s.json' % code)
        try:
            if os.path.exists(cache) and (time.time() - os.path.getmtime(cache)) < 86400:
                import json
                with open(cache, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        try:
            import akshare as ak
            df = _ak_call(lambda: ak.stock_financial_abstract(symbol=code), timeout=5)
            if df is None or df.empty or '指标' not in df.columns:
                return {}
            data_cols = [c for c in df.columns if c != '指标' and c != '选股']
            result = {}
            for key, kw in FUND_KEYWORDS.items():
                rows = df[df['指标'].astype(str).str.contains(kw, na=False)]
                if rows.empty:
                    continue
                vals = []
                for c in data_cols:
                    v = rows.iloc[0].get(c)
                    f = _to_float(v, None) if v is not None else None
                    if f is not None:
                        vals.append(f)
                if vals:
                    result[key] = vals[0]  # 最新一期
            self._save_fin_cache(cache, result)
            return result
        except TimeoutError:
            self._fin_down = True  # 东财财务接口连不上，后续股票不再尝试
            return {}
        except Exception:
            return {}

    def _save_fin_cache(self, cache, result):
        """保存基本面指标到本地缓存（次日自动过期重抓）"""
        try:
            import json
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            with open(cache, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 技术面评分
    # ------------------------------------------------------------------
    def technical_score(self, df):
        """技术面长线评分（0-100）"""
        score = 0.0
        detail = []
        if df is None or df.empty or len(df) < 60:
            return 0.0, detail, {'note': '历史数据不足，无法评估技术面'}

        close = df['收盘'].astype(float)
        n = len(df)
        last = close.iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        ma120 = close.rolling(120).mean().iloc[-1] if n >= 120 else None
        ma250 = close.rolling(250).mean().iloc[-1] if n >= 250 else None

        # 均线多头排列（长线最看重）
        if ma120 is not None:
            if last > ma60 > ma120:
                score += 25
                detail.append('长期均线多头排列（价>MA60>MA120）: +25')
            elif last > ma60:
                score += 15
                detail.append('站上MA60，趋势偏多: +15')
            else:
                score += 5
                detail.append('长期趋势偏弱（价在MA60下方）: +5')
        elif last > ma60:
            score += 20
            detail.append('中期趋势向上（价>MA60）: +20')
        else:
            score += 5
            detail.append('中期趋势偏弱: +5')

        # 长期涨幅（250日）
        if n >= 250:
            ret_250 = (last - close.iloc[-250]) / close.iloc[-250] * 100
            if ret_250 > 50:
                score += 20
                detail.append(f'一年涨幅 {ret_250:.1f}%，长期走牛: +20')
            elif ret_250 > 0:
                score += 12
                detail.append(f'一年涨幅 {ret_250:.1f}%，温和上行: +12')
            else:
                score += 3
                detail.append(f'一年涨幅 {ret_250:.1f}%，长期下行: +3')
        elif n >= 60:
            ret_60 = (last - close.iloc[-60]) / close.iloc[-60] * 100
            if ret_60 > 0:
                score += 12
                detail.append(f'近期涨幅 {ret_60:.1f}%: +12')
            else:
                score += 3
                detail.append(f'近期下跌 {ret_60:.1f}%: +3')

        # 波动率（越低越稳，适合长线）
        daily_ret = close.pct_change().dropna()
        annual_vol = daily_ret.std() * np.sqrt(250) * 100
        if annual_vol < 20:
            score += 15
            detail.append(f'年化波动率 {annual_vol:.1f}%，走势平稳: +15')
        elif annual_vol < 35:
            score += 10
            detail.append(f'年化波动率 {annual_vol:.1f}%，适中: +10')
        elif annual_vol < 55:
            score += 5
            detail.append(f'年化波动率 {annual_vol:.1f}%，偏大: +5')
        else:
            detail.append(f'年化波动率 {annual_vol:.1f}%，波动剧烈: +0')

        # 最大回撤（回撤小更安心长持）
        max_drawdown = self._max_drawdown(close)
        if max_drawdown < 0.15:
            score += 15
            detail.append(f'历史最大回撤 {max_drawdown*100:.1f}%，抗跌: +15')
        elif max_drawdown < 0.30:
            score += 10
            detail.append(f'历史最大回撤 {max_drawdown*100:.1f}%: +10')
        elif max_drawdown < 0.50:
            score += 5
            detail.append(f'历史最大回撤 {max_drawdown*100:.1f}%，较大: +5')
        else:
            detail.append(f'历史最大回撤 {max_drawdown*100:.1f}%，风险高: +0')

        # 距一年高点回撤（当前位置）
        if n >= 250:
            high_250 = close.iloc[-250:].max()
            off_high = (last - high_250) / high_250 * 100
            if off_high >= -5:
                score += 10
                detail.append(f'接近一年高点（回撤 {off_high:.1f}%）: +10')
            elif off_high >= -20:
                score += 6
                detail.append(f'距一年高点回撤 {off_high:.1f}%: +6')
            elif off_high >= -40:
                score += 2
                detail.append(f'距一年高点回撤 {off_high:.1f}%: +2')
            else:
                detail.append(f'距一年高点回撤 {off_high:.1f}%，深跌: +0')

        return score, detail, {'annual_vol': annual_vol, 'max_drawdown': max_drawdown}

    @staticmethod
    def _max_drawdown(close):
        cummax = close.cummax()
        drawdown = (close - cummax) / cummax
        return -drawdown.min()

    # ------------------------------------------------------------------
    # 基本面评分
    # ------------------------------------------------------------------
    def fundamental_score(self, fund):
        """基本面长线评分（0-100）"""
        score = 0.0
        detail = []
        if not fund:
            return 0.0, detail, {'note': '财务数据获取失败'}

        roe = fund.get('roe')
        if roe is not None:
            if roe >= 15:
                score += 25; detail.append(f'净资产收益率(ROE) {roe:.1f}%，盈利能力强: +25')
            elif roe >= 10:
                score += 18; detail.append(f'净资产收益率(ROE) {roe:.1f}%，较好: +18')
            elif roe >= 5:
                score += 10; detail.append(f'净资产收益率(ROE) {roe:.1f}%，一般: +10')
            else:
                score += 2; detail.append(f'净资产收益率(ROE) {roe:.1f}%，偏弱: +2')
        else:
            detail.append('ROE数据缺失')

        rev_growth = fund.get('revenue_growth')
        profit_growth = fund.get('profit_growth')
        if rev_growth is not None:
            if rev_growth > 10:
                score += 20; detail.append(f'营收增速 {rev_growth:.1f}%，成长性好: +20')
            elif rev_growth > 0:
                score += 12; detail.append(f'营收增速 {rev_growth:.1f}%，稳定增长: +12')
            else:
                score += 3; detail.append(f'营收增速 {rev_growth:.1f}%，收入下滑: +3')
        if profit_growth is not None:
            if profit_growth > 10:
                score += 20; detail.append(f'净利润增速 {profit_growth:.1f}%，盈利增长: +20')
            elif profit_growth > 0:
                score += 12; detail.append(f'净利润增速 {profit_growth:.1f}%: +12')
            else:
                score += 3; detail.append(f'净利润增速 {profit_growth:.1f}%，利润下滑: +3')

        margin = fund.get('gross_margin')
        if margin is not None:
            if margin >= 40:
                score += 10; detail.append(f'毛利率 {margin:.1f}%，护城河强: +10')
            elif margin >= 20:
                score += 7; detail.append(f'毛利率 {margin:.1f}%: +7')
            elif margin >= 0:
                score += 3; detail.append(f'毛利率 {margin:.1f}%: +3')

        debt = fund.get('debt_ratio')
        if debt is not None:
            if debt < 30:
                score += 10; detail.append(f'资产负债率 {debt:.1f}%，财务稳健: +10')
            elif debt < 50:
                score += 7; detail.append(f'资产负债率 {debt:.1f}%: +7')
            elif debt < 70:
                score += 3; detail.append(f'资产负债率 {debt:.1f}%，偏高: +3')
            else:
                detail.append(f'资产负债率 {debt:.1f}%，高杠杆: +0')

        cash_profit = fund.get('cash_to_profit')
        if cash_profit is not None:
            if cash_profit >= 0.8:
                score += 15; detail.append(f'经营现金流/净利润 {cash_profit:.2f}，利润含金量高: +15')
            elif cash_profit >= 0:
                score += 8; detail.append(f'经营现金流/净利润 {cash_profit:.2f}: +8')
            else:
                detail.append(f'经营现金流/净利润 {cash_profit:.2f}，利润质量差: +0')

        return score, detail, dict(fund)

    # ------------------------------------------------------------------
    # AI 模型预测
    # ------------------------------------------------------------------
    def ai_prediction(self, df):
        """训练AI模型并预测未来短期走势（0-100）"""
        if df is None or df.empty or len(df) < 70:
            return 50.0, '数据不足，无法训练AI模型', 0.5
        try:
            opt = AIStrategyOptimizer(self.ai_model)
            strategy = AITradingStrategy(self.ai_model, use_ai=False)
            work = df[['收盘', '成交量']].copy()
            ind = strategy.calculate_indicators(work.copy())
            ok = opt.train_model(ind)
            if not ok:
                return 50.0, '历史数据不足以训练AI模型', 0.5
            pred = opt.predict_signal(ind, len(ind) - 1)
            conf = 0.7
            if pred > 0:
                return 85.0, 'AI预测未来偏多（未来5日上涨概率较高）', conf
            elif pred < 0:
                return 20.0, 'AI预测未来偏空（未来5日下跌概率较高）', conf
            return 50.0, 'AI模型认为近期方向不明朗', 0.5
        except Exception as e:
            return 50.0, f'AI预测失败: {e}', 0.5

    # ------------------------------------------------------------------
    # 估值评估
    # ------------------------------------------------------------------
    def valuation_assessment(self, fund, price):
        """基于 EPS 与利润增速做简单估值评估（PE / PEG），返回 dict"""
        try:
            if not fund or price is None or price <= 0:
                return {'pe': None, 'peg': None, 'verdict': '数据不足，无法估值', 'detail': []}
            eps = fund.get('eps')
            if not eps or eps <= 0:
                return {'pe': None, 'peg': None, 'verdict': '亏损股，PE 无意义，注意风险', 'detail': []}
            pe = price / eps
            growth = fund.get('profit_growth')
            peg = pe / (growth * 100) if growth and growth > 0 else None
            if pe < 15:
                verdict = '低估值，安全边际较好'
            elif pe < 30:
                verdict = '估值合理'
            elif pe < 50:
                verdict = '估值偏高，谨慎追高'
            else:
                verdict = '估值过高，注意回调风险'
            detail = [f'市盈率 PE = {pe:.1f}（现价/每股收益）']
            if peg is not None:
                detail.append(f'利润增速 {growth:.1f}%，PEG = {peg:.2f}')
                if peg < 1:
                    detail.append('PEG<1：成长性足以消化当前估值')
                elif peg < 2:
                    detail.append('PEG 1~2：估值与成长基本匹配')
                else:
                    detail.append('PEG>2：估值已透支成长，追高风险大')
            else:
                detail.append('缺利润增速，无法计算 PEG')
            return {'pe': round(pe, 1), 'peg': round(peg, 2) if peg is not None else None,
                    'verdict': verdict, 'detail': detail}
        except Exception:
            return {'pe': None, 'peg': None, 'verdict': '估值数据异常', 'detail': []}

    # ------------------------------------------------------------------
    # 综合分析
    # ------------------------------------------------------------------
    def analyze(self, token, use_ai=True):
        """对一只股票做长线综合诊断，返回报告 dict"""
        t0 = time.time()
        code = None
        name = token
        try:
            syms = self.client.resolve(token)
            if syms and syms[0].type == 'stock':
                code = syms[0].code.zfill(6)
                name = syms[0].name
        except Exception:
            pass
        if not code:
            digits = ''.join(ch for ch in token if ch.isdigit())
            if len(digits) == 6:
                code = digits
            else:
                return {'token': token, 'error': '无法识别该股票，请检查输入'}

        df = self.fetch_history(token if name != token else code, years=3)
        tech_score, tech_detail, tech_meta = self.technical_score(df)
        fund = self.fetch_fundamentals(code)
        fund_score, fund_detail, fund_meta = self.fundamental_score(fund)
        ai_score, ai_text, ai_conf = self.ai_prediction(df) if use_ai else (50.0, '未启用AI预测', 0.5)

        # 综合评分：技术40% + 基本面40% + AI20%
        total = tech_score * 0.4 + fund_score * 0.4 + ai_score * 0.2

        if total >= 80:
            verdict = '优秀，值得长期关注'
            level = 'A'
        elif total >= 65:
            verdict = '良好，适合中长线布局'
            level = 'B'
        elif total >= 50:
            verdict = '一般，需观察或少量配置'
            level = 'C'
        else:
            verdict = '谨慎，长期持有风险较高'
            level = 'D'

        price = None
        if df is not None and not df.empty:
            price = float(df['收盘'].iloc[-1])

        return {
            'token': token,
            'code': code,
            'name': name,
            'price': price,
            'today_change': self._today_change_from_df(df),
            'level': level,
            'total_score': round(total, 1),
            'tech_score': round(tech_score, 1),
            'fund_score': round(fund_score, 1),
            'ai_score': round(ai_score, 1),
            'verdict': verdict,
            'valuation': self.valuation_assessment(fund, price),
            'tech_detail': tech_detail,
            'fund_detail': fund_detail,
            'ai_text': ai_text,
            'ai_conf': ai_conf,
            'history_rows': 0 if df is None else len(df),
            'elapsed': round(time.time() - t0, 1),
        }

    def screen(self, tokens, use_ai=True):
        """批量分析多只股票，返回按总分排序的 DataFrame"""
        rows = []
        for tk in tokens:
            tk = str(tk).strip()
            if not tk:
                continue
            rep = self.analyze(tk, use_ai=use_ai)
            if 'error' in rep:
                rows.append({'输入': tk, '代码': '', '名称': '(无法识别)',
                             '现价': '', '总分': 0, '级别': 'D',
                             '技术面': 0, '基本面': 0, 'AI预测': 0, '结论': rep['error']})
                continue
            rows.append({
                '输入': tk,
                '代码': rep['code'],
                '名称': rep['name'],
                '现价': f"{rep['price']:.2f}" if rep['price'] else '-',
                '总分': rep['total_score'],
                '级别': rep['level'],
                '技术面': rep['tech_score'],
                '基本面': rep['fund_score'],
                'AI预测': rep['ai_score'],
                '结论': rep['verdict'],
            })
        out = pd.DataFrame(rows)
        if not out.empty and '总分' in out.columns:
            out = out.sort_values('总分', ascending=False).reset_index(drop=True)
        return out

    # ------------------------------------------------------------------
    # 全市场快照（供榜单使用）
    # ------------------------------------------------------------------
    def get_market_snapshot(self, use_cache=True, cache_ttl=600):
        """拉取全市场实时快照（多数据源降级：新浪→东财→磁盘缓存）。返回 DataFrame"""
        key = 'all'
        if use_cache:
            cached, fresh, _ = self.client.cache.get('market_snapshot', key)
            if fresh and cached is not None and not cached.empty:
                return cached
        df = self._parallel_sina_spot()
        if df is None or df.empty:
            # 新浪不可达/被限流(456)时，改用东财全市场分页快照
            df = self._parallel_em_spot()
        if df is None or df.empty:
            # 数据源全部失败时，回退最近一次成功的磁盘缓存（数据可能过期但可先用）
            try:
                cached, _, _ = self.client.cache.get('market_snapshot', key)
                if cached is not None and not cached.empty:
                    df = cached
            except Exception:
                pass
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.reset_index(drop=True)
        # 过滤掉 bj 开头的北交所/代码格式
        df['代码6'] = df['代码'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(6)
        df = df[df['代码6'].str.len() == 6]
        if use_cache:
            self.client.cache.set('market_snapshot', key, df)
        return df

    @staticmethod
    def _parallel_sina_spot(workers=8):
        """并行抓取新浪全市场A股快照：分页并发，约 70 页 → 数秒完成。
        返回与 ak.stock_zh_a_spot() 同构的列。"""
        try:
            import requests
            from akshare.utils import demjson
        except Exception:
            import akshare as ak
            return _ak_call(lambda: ak.stock_zh_a_spot(), timeout=45)
        count_url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeStockCount?node=hs_a'
        data_url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
        base = {'num': '80', 'sort': 'symbol', 'asc': '1', 'node': 'hs_a', 'symbol': '', '_s_r_a': 'page'}
        try:
            rc = requests.get(count_url, timeout=10)
            nums = re.findall(r'\d+', rc.text)
            page_count = (int(nums[0]) if nums else 5536) // 80 + 1
        except Exception:
            page_count = 70

        def fetch(page):
            p = dict(base)
            p['page'] = str(page)
            resp = requests.get(data_url, params=p, timeout=20)
            return demjson.decode(resp.text)

        pages = []
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(fetch, pg) for pg in range(1, page_count + 1)]
            for f in as_completed(futs):
                try:
                    d = f.result()
                    if isinstance(d, list) and d:
                        pages.append(d)
                except Exception:
                    pass
        all_rows = [row for d in pages for row in d]
        if not all_rows:
            return pd.DataFrame()
        colmap = {'symbol': '代码', 'name': '名称', 'trade': '最新价', 'pricechange': '涨跌额',
                  'changepercent': '涨跌幅', 'buy': '买入', 'sell': '卖出', 'settlement': '昨收',
                  'open': '今开', 'high': '最高', 'low': '最低', 'volume': '成交量',
                  'amount': '成交额', 'ticktime': '时间戳'}
        out = pd.DataFrame([{colmap[k]: v for k, v in row.items() if k in colmap} for row in all_rows])
        return out

    @staticmethod
    def _parallel_em_spot(workers=4):
        """东方财富全市场A股快照（push2 clist 分页），作为新浪不可达时的第二数据源。
        返回与 _parallel_sina_spot 同构的列。"""
        try:
            import requests
        except Exception:
            return pd.DataFrame()
        url = 'https://push2.eastmoney.com/api/qt/clist/get'
        base = {
            'pn': '1', 'pz': '500', 'po': '1', 'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2', 'invt': '2', 'fid': 'f6',
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048',
            'fields': 'f2,f3,f4,f5,f6,f8,f12,f14,f15,f16,f17,f18,f20,f23',
        }
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
        page_count = 12
        try:
            rc = requests.get(url, params=dict(base), headers=headers, timeout=10)
            data = rc.json().get('data') or {}
            total = int(data.get('total') or 0)
            if total > 0:
                page_count = (total + int(base['pz']) - 1) // int(base['pz'])
        except Exception:
            pass

        def fetch(page):
            p = dict(base)
            p['pn'] = str(page)
            resp = requests.get(url, params=p, headers=headers, timeout=20)
            d = resp.json().get('data') or {}
            diff = d.get('diff') or []
            if isinstance(diff, dict):  # 单页偶发返回 dict 而非 list
                diff = list(diff.values())
            return diff

        rows = []
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(fetch, pg) for pg in range(1, page_count + 1)]
            for f in as_completed(futs):
                try:
                    diff = f.result()
                    if not isinstance(diff, list):
                        continue
                    for it in diff:
                        try:
                            code = str(it.get('f12', '')).zfill(6)
                            if not code:
                                continue
                            rows.append({
                                '代码': code,
                                '名称': str(it.get('f14', '') or ''),
                                '最新价': _to_float(it.get('f2')),
                                '涨跌额': _to_float(it.get('f4')),
                                '涨跌幅': _to_float(it.get('f3')),
                                '昨收': _to_float(it.get('f18')),
                                '今开': _to_float(it.get('f17')),
                                '最高': _to_float(it.get('f15')),
                                '最低': _to_float(it.get('f16')),
                                '成交量': int(_to_float(it.get('f5'))) * 100,  # 手→股
                                '成交额': _to_float(it.get('f6')),
                                '时间戳': time.strftime('%H:%M:%S'),
                            })
                        except Exception:
                            pass
                except Exception:
                    pass
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # 长线榜单
    # ------------------------------------------------------------------
    def screen_longterm(self, limit=10, use_ai=True, progress_cb=None):
        """
        自动扫描全市场，先用实时快照做初筛（排除ST/低价/超小成交额），
        再对候选逐只跑长线深度分析，返回按总分排序的榜单 DataFrame。
        progress_cb(name, done_count, target) 每分析完一只回调一次，用于界面显示进度。
        """
        snap = self.get_market_snapshot()
        if snap is None or snap.empty:
            # 新浪临时被限流(456)时，退回最近一次成功的缓存快照
            try:
                cached, _, _ = self.client.cache.get('market_snapshot', 'all')
                if cached is not None and not cached.empty:
                    snap = cached
            except Exception:
                pass
        if snap is None or snap.empty:
            return pd.DataFrame()
        # 初筛条件
        try:
            snap['最新价'] = pd.to_numeric(snap['最新价'], errors='coerce')
            snap['成交额'] = pd.to_numeric(snap['成交额'], errors='coerce')
            snap['涨跌幅'] = pd.to_numeric(snap['涨跌幅'], errors='coerce')
        except Exception:
            pass
        name = snap['名称'].astype(str)
        # 排除ST/退市、低价(<4元)、成交额过低(<5000万)
        mask = (~name.str.contains('ST', case=False, na=False)) \
            & (~name.str.contains('退', na=False)) \
            & (snap['最新价'].fillna(0) >= 4) \
            & (snap['成交额'].fillna(0) >= 5e7)
        candidates = snap[mask].copy()
        if candidates.empty:
            candidates = snap.copy()
        # 优先成交额大的（流动性好），取部分候选跑深度分析（数量大时适当压缩池子提速）
        candidates = candidates.sort_values('成交额', ascending=False).head(max(limit * 2, 30))
        rows = []
        budget = 90.0 + limit * 2.0   # 整体时间预算（秒）：随数量增大，超时返回已分析的部分结果
        t0 = time.time()
        fail_streak = 0

        def _run(code, use_ai):
            return self.analyze(code, use_ai=use_ai)

        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(_run, r['代码6'], use_ai): (r['代码6'], r['名称'], r)
                    for _, r in candidates.iterrows()}
            for f in as_completed(futs):
                if time.time() - t0 > budget:
                    break
                code, nm, r = futs[f]
                try:
                    rep = f.result()
                except Exception:
                    continue
                if 'error' in rep:
                    fail_streak += 1
                    if fail_streak >= 3:  # 多只连续失败（多为数据源连不上），提前结束避免卡死
                        break
                    continue
                fail_streak = 0
                # 今日涨幅：盘中用快照实时值，收盘后快照涨幅可能为0，改用历史日线兜底
                tc = rep.get('today_change')
                if tc is None:
                    tc = self._snap_pct(r)
                rows.append({
                    '排名': len(rows) + 1,
                    '代码': rep['code'],
                    '名称': rep['name'],
                    '现价': f"{rep['price']:.2f}" if rep['price'] else '-',
                    '总分': rep['total_score'],
                    '级别': rep['level'],
                    '技术面': rep['tech_score'],
                    '基本面': rep['fund_score'],
                    'AI预测': rep['ai_score'],
                    '结论': rep['verdict'],
                    '今涨跌幅': f"{tc:+.2f}%" if tc is not None else '-',
                    '长期影响指数': rep['total_score'],
                })
                if progress_cb:
                    progress_cb(nm, len(rows), limit)
                if len(rows) >= limit:
                    break
        out = pd.DataFrame(rows)
        if not out.empty:
            out['排名'] = range(1, len(out) + 1)
            out = out.sort_values('总分', ascending=False).reset_index(drop=True)
            out['排名'] = range(1, len(out) + 1)
        return out

    @staticmethod
    def _snap_pct(r):
        try:
            return float(r.get('涨跌幅', 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _today_change_from_df(df):
        """基于历史日线计算今日涨跌幅(%)，收盘后快照涨幅为0时用它兜底"""
        try:
            if df is None or df.empty or len(df) < 2:
                return None
            c = df['收盘'].astype(float)
            last = float(c.iloc[-1])
            prev = float(c.iloc[-2])
            if prev and prev > 0:
                return (last - prev) / prev * 100
        except Exception:
            pass
        return None

    @staticmethod
    def _ret_from_df(df, n=5):
        """近 n 个交易日涨幅(%)，数据不足返回 None"""
        try:
            if df is None or df.empty or len(df) < n + 1:
                return None
            c = df['收盘'].astype(float)
            last = float(c.iloc[-1])
            prev = float(c.iloc[-1 - n])
            if prev and prev > 0:
                return (last - prev) / prev * 100
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # 短线榜单
    # ------------------------------------------------------------------
    def screen_budget(self, total, n=10, mode='hot'):
        """
        按总金额从全市场挑选买得起的股票（独立于榜单，小资金友好）。
        1手=100股，要求 1手成本 <= total；排除 ST/退/北交所/B股。
        mode='mix'：综合判断（默认），动量双向权衡+量能+低价+位置，既给活跃又给超跌机会，防追高防接刀；
        mode='hot'：追高型，涨幅+量能+低价加分（选活跃上涨股）；
        mode='dip'：抄底型，当日超跌+流动性+低价+接近当日低点加分（选跌下来的）。
        返回字段：排名/代码/名称/现价/1手成本/活跃分/涨跌幅。
        """
        total = float(total or 0)
        if total <= 0:
            return pd.DataFrame()
        mode = str(mode or 'mix')
        snap = self.get_market_snapshot()
        if snap is None or snap.empty:
            # 新浪临时被限流(456)时，退回最近一次成功的缓存快照
            try:
                cached, _, _ = self.client.cache.get('market_snapshot', 'all')
                if cached is not None and not cached.empty:
                    snap = cached
            except Exception:
                pass
        if snap is None or snap.empty:
            return pd.DataFrame()
        try:
            snap['最新价'] = pd.to_numeric(snap['最新价'], errors='coerce')
            snap['昨收'] = pd.to_numeric(snap['昨收'], errors='coerce')
            snap['成交额'] = pd.to_numeric(snap['成交额'], errors='coerce')
            snap['最高'] = pd.to_numeric(snap['最高'], errors='coerce')
            snap['最低'] = pd.to_numeric(snap['最低'], errors='coerce')
        except Exception:
            pass
        price = snap['最新价'].fillna(0)
        price = price.where(price > 0, snap['昨收'].fillna(0))
        snap['price'] = price
        name = snap['名称'].astype(str)
        code6 = snap['代码6'].astype(str)
        mask = (~name.str.contains('ST', case=False, na=False)) \
            & (~name.str.contains('退', na=False)) \
            & (~code6.str.startswith(('2', '4', '8', '9'))) \
            & (price > 0) & (price * 100 <= total)
        snap = snap[mask].copy()
        if snap.empty:
            return pd.DataFrame()

        scored = []
        for _, r in snap.iterrows():
            p = float(r.get('price') or 0)
            pct = self._snap_pct(r)
            amt = float(r.get('成交额') or 0)
            if mode == 'dip':
                # ---- 抄底型：当日跌得越深分越高，避免追高 ----
                if pct <= -7:
                    sg = 40
                elif pct <= -5:
                    sg = 35
                elif pct <= -3.5:
                    sg = 28
                elif pct <= -2:
                    sg = 18
                elif pct <= 0:
                    sg = 10
                elif pct <= 3:
                    sg = 5
                else:
                    sg = 0
                # 流动性：成交额适中（有承接又没放天量出逃）
                if 5e8 <= amt <= 2e9:
                    sa = 25
                elif 2e8 <= amt < 5e8 or 2e9 < amt <= 5e9:
                    sa = 15
                elif 5e7 <= amt < 2e8 or amt > 5e9:
                    sa = 7
                else:
                    sa = 2
                # 接近当日低点加分：现价仍贴近最低价 = 弱势未反弹，留了抄底空间
                h = float(r.get('最高') or 0)
                l = float(r.get('最低') or 0)
                near_low = 0
                if h > l > 0:
                    pos = (p - l) / (h - l)
                    if pos <= 0.25:
                        near_low = 20
                    elif pos <= 0.45:
                        near_low = 12
                    elif pos <= 0.65:
                        near_low = 5
            elif mode == 'mix':
                # ---- 综合判断：动量双向权衡（超跌与强势都给分，涨停/跌停降权防追高防接刀）+ 量能 + 低价 + 位置 ----
                if pct <= -9.5 or pct >= 9.5:
                    sg = 15
                elif pct <= -7:
                    sg = 38
                elif pct <= -4:
                    sg = 34
                elif pct <= -2:
                    sg = 26
                elif pct <= 0:
                    sg = 16
                elif pct <= 2:
                    sg = 18
                elif pct <= 4:
                    sg = 30
                elif pct <= 6:
                    sg = 36
                else:
                    sg = 32
                # 流动性：成交额适中（有承接又没放天量出逃）
                if 5e8 <= amt <= 2e9:
                    sa = 25
                elif 2e8 <= amt < 5e8 or 2e9 < amt <= 5e9:
                    sa = 15
                elif 5e7 <= amt < 2e8 or amt > 5e9:
                    sa = 7
                else:
                    sa = 2
                near_low = 0
            else:
                # ---- 追高型（原逻辑）：涨幅越高分越高 ----
                if pct >= 9.5:
                    sg = 30
                elif pct >= 5:
                    sg = 40
                elif pct >= 2:
                    sg = 30
                elif pct >= 0:
                    sg = 15
                elif pct >= -2:
                    sg = 5
                else:
                    sg = 0
                if amt >= 2e9:
                    sa = 25
                elif amt >= 1e9:
                    sa = 20
                elif amt >= 5e8:
                    sa = 14
                elif amt >= 2e8:
                    sa = 8
                else:
                    sa = 4
                near_low = 0
            low = 0
            if p <= 2:
                low = 15
            elif p <= 3:
                low = 12
            elif p <= 5:
                low = 8
            elif p <= 8:
                low = 4
            scored.append((sg + sa + low + near_low, r))
        scored.sort(key=lambda x: x[0], reverse=True)

        out = []
        for i, (score, r) in enumerate(scored[:max(int(n or 10), 10)]):
            p = float(r.get('price') or 0)
            out.append({
                '排名': i + 1,
                '代码': r.get('代码6', ''),
                '名称': r.get('名称', ''),
                '现价': round(p, 2),
                '1手成本': round(p * 100, 2),
                '活跃分': score,
                '涨跌幅': round(self._snap_pct(r), 2),
            })
        return pd.DataFrame(out)

    def screen_shortterm(self, limit=10):
        """
        基于全市场实时快照做短线多因子打分：
        涨幅占40%，量能(成交额)占25%，换手活跃度占20%，走势强度(收于当日高位)占15%。
        盘中：涨幅=实时浮动的今日涨幅，实时刷新；
        收盘：今日涨幅以历史日线兜底（快照可能为0），榜单以"5日涨幅"为准并给出5日涨幅列。
        返回字段：代码/名称/最新价/涨跌幅(今日)/5日涨幅/短线分/提示。
        """
        snap = self.get_market_snapshot()
        if snap is None or snap.empty:
            return pd.DataFrame()
        try:
            snap['最新价'] = pd.to_numeric(snap['最新价'], errors='coerce')
            snap['涨跌幅'] = pd.to_numeric(snap['涨跌幅'], errors='coerce')
            snap['成交额'] = pd.to_numeric(snap['成交额'], errors='coerce')
            snap['最高'] = pd.to_numeric(snap['最高'], errors='coerce')
            snap['最低'] = pd.to_numeric(snap['最低'], errors='coerce')
        except Exception:
            pass
        name = snap['名称'].astype(str)
        has_vol = int((snap['成交额'].fillna(0) > 0).sum())     # 盘前/非交易时成交额多为0
        has_price = int((snap['最新价'].fillna(0) > 0).sum())   # 盘前最新价为0，昨收有效
        snap['昨收'] = pd.to_numeric(snap['昨收'], errors='coerce')
        eff_price = snap['最新价'].fillna(0)
        eff_price = eff_price.where(eff_price > 0, snap['昨收'])  # 盘前用昨收代替现价
        mask = (~name.str.contains('ST', case=False, na=False)) \
            & (~name.str.contains('退', na=False)) \
            & (eff_price.fillna(0) >= 4)
        if has_vol > 50 and has_price > 50:
            # 正常交易日：只看成交额>1亿的活跃股
            mask = mask & (snap['成交额'].fillna(0) >= 1e8)
        snap['最新价'] = eff_price
        snap = snap[mask].copy()
        if snap.empty:
            return pd.DataFrame()

        score_list = []
        for _, r in snap.iterrows():
            pct = self._snap_pct(r)
            amount = r.get('成交额', 0) or 0
            high = r.get('最高', 0) or 0
            low = r.get('最低', 0) or 0
            last = r.get('最新价', 0) or 0

            # 涨幅分 (0-40)：温和上涨最优，涨停过高
            if pct >= 9.5:
                score_gain = 30  # 涨停，追高风险
            elif pct >= 5:
                score_gain = 40
            elif pct >= 2:
                score_gain = 30
            elif pct >= 0:
                score_gain = 15
            elif pct >= -2:
                score_gain = 5
            else:
                score_gain = 0

            # 量能分 (0-25)
            if amount >= 2e9:
                score_amt = 25
            elif amount >= 1e9:
                score_amt = 20
            elif amount >= 5e8:
                score_amt = 14
            elif amount >= 2e8:
                score_amt = 8
            else:
                score_amt = 4

            # 走势强度分 (0-15)：收盘接近当日最高 = 强势
            try:
                if high and high > low:
                    pos = (last - low) / (high - low)
                    score_pos = round(pos * 15)
                else:
                    score_pos = 7
            except Exception:
                score_pos = 7

            # 波动分 (0-20)：振幅适中有机会，过小太平淡
            try:
                pre_close = r.get('昨收', 0) or 0
                if pre_close:
                    amp = (high - low) / pre_close * 100
                    if 3 <= amp <= 8:
                        score_amp = 20
                    elif 1 <= amp < 3:
                        score_amp = 12
                    elif amp > 8:
                        score_amp = 8
                    else:
                        score_amp = 4
                else:
                    score_amp = 8
            except Exception:
                score_amp = 8

            total = score_gain + score_amt + score_pos + score_amp
            score_list.append((total, score_gain, score_amt, score_pos, score_amp, r))

        score_list.sort(key=lambda x: x[0], reverse=True)
        # 收盘/盘前无成交量数据时无法按量能挑活跃股，扩大候选池避免空榜
        pool_n = max(limit * 4, 300) if has_vol <= 50 else max(limit * 3, 30)
        pool = score_list[:pool_n]

        intraday = self.is_trading_time()
        if intraday:
            # 盘中：用快照实时涨幅秒出结果，同时按需算 5日涨幅（只算上榜个股，避免拖慢）
            top = pool[:limit]
            ret5_map = {}

            def _calc_ret5(code):
                try:
                    df = self.fetch_history(code, years=1)
                    return code, self._ret_from_df(df, 5)
                except Exception:
                    return code, None

            with ThreadPoolExecutor(max_workers=10) as ex:
                futs = {ex.submit(_calc_ret5, ent[5].get('代码6', '')): None for ent in top}
                for f in as_completed(futs):
                    try:
                        code, ret5 = f.result()
                        ret5_map[code] = ret5
                    except Exception:
                        pass

            rows = []
            for i, (total, sg, sa, sp, sam, r) in enumerate(top):
                pct = self._snap_pct(r)
                ret5 = ret5_map.get(r.get('代码6', ''))
                rows.append({
                    '排名': i + 1,
                    '代码': r.get('代码6', ''),
                    '名称': r.get('名称', ''),
                    '最新价': f"{self._num(r.get('最新价')):.2f}",
                    '短线分': total,
                    '涨跌幅': round(pct, 2),
                    '5日涨幅': round(ret5, 2) if ret5 is not None else None,
                    '今涨跌幅': f"{pct:+.2f}%",
                    '成交额': self._fmt_amount(r.get('成交额')),
                    '强度': f"{sp}",
                    '提示': '强势上涨' if total >= 80 else ('关注' if total >= 65 else '观察'),
                })
            return pd.DataFrame(rows)

        # 收盘：抓历史日线算5日涨幅/今日涨幅，榜单以5日涨幅为准
        def _calc(code):
            df = self.fetch_history(code, years=1)
            return code, self._ret_from_df(df, 5), self._today_change_from_df(df)

        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(_calc, r.get('代码6', '')): (sg2, sa2, sp2, sam2, r)
                    for (t, sg2, sa2, sp2, sam2, r) in pool}
            results = {}
            for f in as_completed(futs):
                try:
                    code, ret5, today = f.result()
                    results[code] = (ret5, today)
                except Exception:
                    pass

        rows = []
        built = []
        for (total, sg, sa, sp, sam, r) in pool:
            code = r.get('代码6', '')
            ret5, today = results.get(code, (None, None))
            # 收盘后：以5日涨幅为核心重打分（量能仍用快照）
            p5 = ret5 if ret5 is not None else self._snap_pct(r)
            if p5 >= 20:
                g5 = 40
            elif p5 >= 10:
                g5 = 40
            elif p5 >= 5:
                g5 = 30
            elif p5 >= 2:
                g5 = 20
            elif p5 >= 0:
                g5 = 10
            else:
                g5 = 0
            score = g5 + sa + sp + sam
            tc = today if today is not None else self._snap_pct(r)
            built.append((score, code, r.get('名称', ''), self._num(r.get('最新价')),
                          tc, ret5, sa, sp, total))
        built.sort(key=lambda x: x[0], reverse=True)
        for i, (score, code, nm, price, tc, ret5, sa, sp, snap_total) in enumerate(built[:limit]):
            rows.append({
                '排名': i + 1,
                '代码': code,
                '名称': nm,
                '最新价': f"{price:.2f}",
                '短线分': score,
                '涨跌幅': round(tc, 2),
                '5日涨幅': round(ret5, 2) if ret5 is not None else None,
                '今涨跌幅': f"{tc:+.2f}%",
                '成交额': self._fmt_amount(r.get('成交额')),
                '强度': f"{sp}",
                '提示': '强势上涨' if score >= 80 else ('关注' if score >= 65 else '观察'),
            })
        return pd.DataFrame(rows)

    @staticmethod
    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _fmt_amount(v):
        try:
            v = float(v)
            if v >= 1e8:
                return f"{v/1e8:.1f}亿"
            return f"{v/1e4:.0f}万"
        except (TypeError, ValueError):
            return '-'


def _demo():
    """命令行自测"""
    ana = LongTermAnalyzer()
    for token in ['600519', '000858', '601318']:
        rep = ana.analyze(token)
        print('=' * 60)
        print(f"{rep.get('name')}({rep.get('code')}) 现价 {rep.get('price')}")
        print(f"总分 {rep.get('total_score')}  级别 {rep.get('level')}  {rep.get('verdict')}")
        print(f"  技术面 {rep.get('tech_score')}  基本面 {rep.get('fund_score')}  AI {rep.get('ai_score')}")
        for d in rep.get('tech_detail', [])[:3]:
            print('  [技术]', d)
        for d in rep.get('fund_detail', [])[:3]:
            print('  [基本面]', d)
        print('  [AI]', rep.get('ai_text'))


if __name__ == '__main__':
    _demo()


