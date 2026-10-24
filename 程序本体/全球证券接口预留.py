# -*- coding: utf-8 -*-
"""
全球证券接口预留模块（港股 / 美股 / 其他海外市场）
=====================================================
用户尚未开通港股 / 美股证券账户，本模块负责：

1. 预留统一的市场扩展层（MarketRegistry），未来开通账户后只需实现
   `TradeGateway` 接口即可接入真实下单，无需改动上层业务。
2. 行情 / 历史 / 基本面 / 财报 / 公告 数据源已预留（akshare hk/us 接口），
   当前状态标记为"数据可用，交易未开通"。
3. 持仓与账户管理：预留 `GlobalPortfolio`（独立于 A 股 portfolio.pkl），
   开通账户前也可先记录"观察仓 / 模拟仓"。
4. 交易网关接口（TradeGateway）：占位实现 `PlaceholderGateway`，
   明确抛出"账户未开通"，并返回统一错误码，方便上层识别。

设计原则：
- 不引入新的第三方依赖（复用 akshare / requests / pandas）。
- 所有接口保持"能跑通、能返回结构化结果"，避免上层出现 KeyError。
- 市场代码规范：
    港股  code='00700'  market='hk'  secid='116.00700'
    美股  code='AAPL'   market='us'  secid='106.AAPL'
    沪A   code='600519' market='sh'  secid='1.600519'
    深A   code='000001' market='sz'  secid='0.000001'
"""

import os
import sys
import json
import time
import datetime
import threading

sys.path.append(os.path.dirname(__file__))

try:
    import akshare as ak
except ImportError:
    ak = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import requests
except ImportError:
    requests = None


# ----------------------------------------------------------------------------
# 市场注册表
# ----------------------------------------------------------------------------
class MarketInfo:
    """单个市场的元信息（预留字段，后续开通账户时填写）"""

    def __init__(self, market, name, currency, tz,
                 secid_prefix='', trade_gateway_cls=None,
                 account_opened=False, data_ready=False,
                 min_lot=1, timezones=''):
        self.market = market              # 'hk' / 'us' / 'sh' / 'sz' / 'other'
        self.name = name                 # 展示名
        self.currency = currency         # HKD / USD / CNY
        self.tz = tz                     # IANA 时区
        self.secid_prefix = secid_prefix  # 东财 secid 前缀（hk=116, us=105/106/107）
        self.trade_gateway_cls = trade_gateway_cls  # 未来实现的 TradeGateway
        self.account_opened = account_opened        # 是否已开通证券账户
        self.data_ready = data_ready                # 行情数据是否已接入
        self.min_lot = min_lot                          # 最小交易单位
        self.notes = []

    def add_note(self, note):
        self.notes.append(note)

    def to_dict(self):
        return {
            'market': self.market,
            'name': self.name,
            'currency': self.currency,
            'timezone': self.tz,
            'secid_prefix': self.secid_prefix,
            'account_opened': self.account_opened,
            'data_ready': self.data_ready,
            'min_lot': self.min_lot,
            'notes': list(self.notes),
            'gateway': getattr(self.trade_gateway_cls, '__name__', None),
        }


class MarketRegistry:
    """多市场注册表。未来开通账户时只需 register(...) 即可。"""

    _KNOWN = {
        'hk': dict(name='港股', currency='HKD', tz='Asia/Hong_Kong',
                    secid_prefix='116', min_lot=1),
        'us': dict(name='美股', currency='USD', tz='America/New_York',
                    secid_prefix='105', min_lot=1),
        'sh': dict(name='沪A', currency='CNY', tz='Asia/Shanghai',
                    secid_prefix='1', min_lot=100),
        'sz': dict(name='深A', currency='CNY', tz='Asia/Shanghai',
                    secid_prefix='0', min_lot=100),
    }

    def __init__(self):
        self._markets = {}
        for m, meta in self._KNOWN.items():
            info = MarketInfo(m, **meta)
            if m in ('sh', 'sz'):
                info.account_opened = True
                info.data_ready = True
                info.trade_gateway_cls = None  # 走 A 股既有 EasyTraderAPI
            else:
                info.account_opened = False
                info.data_ready = True  # 行情数据已接入，交易未开通
                info.trade_gateway_cls = PlaceholderTradeGateway
            self._markets[m] = info

    def get(self, market):
        return self._markets.get(market)

    def all(self):
        return list(self._markets.values())

    def list(self):
        return [m.to_dict() for m in self._markets.values()]

    def register(self, market, name, currency, tz,
                 secid_prefix='', trade_gateway_cls=None,
                 account_opened=False, data_ready=False, min_lot=1):
        """注册新市场（如期货 / 外汇 / 加密），幂等。"""
        if market in self._markets:
            info = self._markets[market]
            info.name = name
            info.currency = currency
            info.tz = tz
            info.secid_prefix = secid_prefix or info.secid_prefix
            info.trade_gateway_cls = trade_gateway_cls or info.trade_gateway_cls
            info.account_opened = account_opened
            info.data_ready = data_ready
            info.min_lot = min_lot
            return info
        info = MarketInfo(market, name, currency, tz,
                          secid_prefix=secid_prefix,
                          trade_gateway_cls=trade_gateway_cls,
                          account_opened=account_opened,
                          data_ready=data_ready,
                          min_lot=min_lot)
        self._markets[market] = info
        return info

    def resolve_market(self, code, hint=''):
        """从代码 / 提示词推断市场。hint 可传 'hk' / 'us' / 'sh' / 'sz'。"""
        code = str(code).strip()
        if hint:
            return hint
        c = code.lower()
        # 含字母 → 大概率美股（ticker）
        if any(ch.isalpha() for ch in c):
            return 'us'
        # 6 位纯数字：港股 / A 股，无法仅凭代码区分，调用方需显式指定
        if c.isdigit() and len(c) == 6:
            return 'hk'
        return 'hk'


# ----------------------------------------------------------------------------
# 预留交易网关（未开通账户时占位）
# ----------------------------------------------------------------------------
class TradeGateway:
    """未来接入真实券商 API 时实现的接口（港美股）。"""

    # 统一错误码
    ERR_NOT_OPENED = 'GATEWAY_NOT_OPENED'
    ERR_NETWORK = 'GATEWAY_NETWORK'
    ERR_INVALID = 'GATEWAY_INVALID'
    ERR_UNSUPPORTED = 'GATEWAY_UNSUPPORTED'

    def __init__(self, market='hk'):
        self.market = market
        self.state = 'disabled'  # disabled / connected / error

    def connect(self, user='', password='', broker=''):
        """预留：连接券商 API。默认未开通，直接抛占位异常。"""
        raise NotImplementedError(
            f"[{self.market}] 交易网关未实现：账户未开通，仅预留接口")

    def get_positions(self):
        raise NotImplementedError(f"[{self.market}] 账户未开通")

    def get_balance(self):
        raise NotImplementedError(f"[{self.market}] 账户未开通")

    def place_order(self, code, side, volume, price=0.0, order_type='limit'):
        """预留：下单。side in ('buy','sell','long','short')。"""
        raise NotImplementedError(f"[{self.market}] 账户未开通，无法下单")

    def cancel_order(self, order_id):
        raise NotImplementedError(f"[{self.market}] 账户未开通")

    def get_orders(self, status='all'):
        raise NotImplementedError(f"[{self.market}] 账户未开通")


class PlaceholderTradeGateway(TradeGateway):
    """占位网关：所有方法返回结构化"未开通"结果，方便上层统一处理。"""

    def connect(self, user='', password='', broker=''):
        self.state = 'disabled'
        return {'ok': False, 'code': self.ERR_NOT_OPENED,
                'msg': f'{self.market} 交易网关尚未开通，当前为预留接口'}

    def get_positions(self):
        return {'ok': False, 'code': self.ERR_NOT_OPENED,
                'msg': f'{self.market} 账户未开通', 'positions': []}

    def get_balance(self):
        return {'ok': False, 'code': self.ERR_NOT_OPENED,
                'msg': f'{self.market} 账户未开通', 'balance': 0.0}

    def place_order(self, code, side, volume, price=0.0, order_type='limit'):
        return {'ok': False, 'code': self.ERR_NOT_OPENED,
                'msg': f'{self.market} 账户未开通，下单被预留接口拦截',
                'order_id': None}

    def cancel_order(self, order_id):
        return {'ok': False, 'code': self.ERR_NOT_OPENED,
                'msg': f'{self.market} 账户未开通'}

    def get_orders(self, status='all'):
        return {'ok': False, 'code': self.ERR_NOT_OPENED,
                'msg': f'{self.market} 账户未开通', 'orders': []}


# ----------------------------------------------------------------------------
# 全球行情数据源（预留，数据已接入）
# ----------------------------------------------------------------------------
class GlobalMarketData:
    """港美股行情 / 历史 / 财报 / 公告 数据源封装。

    全部走 akshare 的 hk/us 接口；任何一项失败都返回结构化 dict，
    避免上层 KeyError。
    """

    # 东财 secid 前缀（与 Symbol.secid 规则保持一致）
    SECID_PREFIX = {
        'hk': '116',
        'us': '105',
    }

    def __init__(self, registry=None):
        self.registry = registry or MarketRegistry()
        self._req = requests if requests else None
        self._lock = threading.Lock()
        self._cache = {}      # (market, code, kind) -> (ts, payload)
        self._cache_ttl = 60  # 秒

    # ---------- 工具 ----------
    @staticmethod
    def _now_ts():
        return time.time()

    def _cache_get(self, market, code, kind):
        key = (market, str(code).upper(), kind)
        with self._lock:
            hit = self._cache.get(key)
            if hit and (self._now_ts() - hit[0]) < self._cache_ttl:
                return hit[1]
        return None

    def _cache_set(self, market, code, kind, payload):
        key = (market, str(code).upper(), kind)
        with self._lock:
            self._cache[key] = (self._now_ts(), payload)
            # 简单清理
            if len(self._cache) > 500:
                oldest = sorted(self._cache, key=lambda k: self._cache[k][0])[:100]
                for k in oldest:
                    self._cache.pop(k, None)

    @staticmethod
    def _norm_code(code, market):
        code = str(code).strip()
        if market == 'hk':
            return code.zfill(5)
        return code.upper()

    # ---------- 实时行情 ----------
    def realtime(self, codes, market='hk'):
        """批量实时行情。codes: 代码列表。market: 'hk'/'us'。

        实现：东财 push2 ulist，secids 形如 '116.00700'。
        未开通账户也可调用，因为行情数据独立于交易。
        """
        codes = [self._norm_code(c, market) for c in codes]
        cached = self._cache_get(market, ','.join(codes), 'rt')
        if cached is not None:
            return {'ok': True, 'rows': cached, 'from_cache': True}

        if self._req is None or not codes:
            return {'ok': False, 'rows': [],
                    'msg': '行情数据源不可用（requests 未安装或代码为空）'}

        prefix = self.SECID_PREFIX.get(market, '116')
        url = 'https://push2.eastmoney.com/api/qt/ulist.np/get'
        out = []
        for i in range(0, len(codes), 60):
            batch = codes[i:i + 60]
            secids = ','.join([f'{prefix}.{c}' for c in batch])
            params = {'secids': secids, 'fltt': 2, 'invt': 2,
                      'fields': 'f1,f2,f3,f4,f5,f6,f7,f12,f14,f15,f16,f17,f18'}
            try:
                r = self._req.get(url, params=params, timeout=8,
                                   headers={'User-Agent': 'Mozilla/5.0',
                                            'Referer': 'https://quote.eastmoney.com/'})
                data = (r.json().get('data') or {}).get('diff') or []
                for d in data:
                    out.append({
                        'code': str(d.get('f12', '')),
                        'name': d.get('f14', ''),
                        'price': d.get('f2'),
                        'pct': d.get('f3'),
                        'change': d.get('f4'),
                        'volume': d.get('f5'),
                        'amount': d.get('f6'),
                        'amplitude': d.get('f7'),
                    })
            except Exception as e:
                return {'ok': False, 'rows': out,
                        'msg': f'{market} 行情获取失败: {e}'}
        self._cache_set(market, ','.join(codes), 'rt', out)
        return {'ok': True, 'rows': out, 'from_cache': False}

    # ---------- 历史K线 ----------
    def history(self, code, market='hk', years=2, start_date='', end_date=''):
        """历史日线。akshare: stock_hk_hist / stock_us_hist。"""
        if ak is None:
            return {'ok': False, 'msg': 'akshare 未安装', 'df': None}
        c = self._norm_code(code, market)
        cached = self._cache_get(market, c, 'hist')
        if cached is not None:
            return {'ok': True, 'rows': cached, 'from_cache': True}

        fn = getattr(ak, 'stock_hk_hist' if market == 'hk'
                    else 'stock_us_hist', None)
        if fn is None:
            return {'ok': False, 'msg': f'{market} 历史接口不可用', 'df': None}
        end = end_date or datetime.date.today().strftime('%Y%m%d')
        start_dt = datetime.date.today() - datetime.timedelta(days=int(years * 365))
        start = start_date or start_dt.strftime('%Y%m%d')
        try:
            if market == 'us':
                # 美股需要交易所前缀，105=NASDAQ / 106=NYSE
                sym = f'105.{c}'
                df = fn(symbol=sym, period='daily',
                        start_date=start, end_date=end, adjust='')
            else:
                df = fn(symbol=c, period='daily',
                        start_date=start, end_date=end, adjust='')
        except Exception as e:
            return {'ok': False, 'msg': f'{market} 历史K线获取失败: {e}',
                    'df': None}
        if df is None or df.empty:
            return {'ok': True, 'rows': [], 'msg': '无数据', 'df': None}
        # 规整为统一列
        if 'date' in df.columns:
            df = df.rename(columns={
                'date': '日期', 'open': '开盘', 'high': '最高',
                'low': '最低', 'close': '收盘', 'volume': '成交量',
                'amount': '成交额'})
        rows = df.tail(500).to_dict('records')
        self._cache_set(market, c, 'hist', rows)
        return {'ok': True, 'rows': rows, 'from_cache': False, 'df': df}

    # ---------- 财报 ----------
    def financial_report(self, code, market='hk', symbol='资产负债表',
                         indicator='按年度'):
        """财报。akshare: stock_financial_hk_report_em / stock_financial_us_report_em。"""
        if ak is None:
            return {'ok': False, 'msg': 'akshare 未安装', 'df': None}
        c = self._norm_code(code, market)
        fn = getattr(ak, 'stock_financial_hk_report_em' if market == 'hk'
                    else 'stock_financial_us_report_em', None)
        if fn is None:
            return {'ok': False, 'msg': f'{market} 财报接口不可用', 'df': None}
        try:
            if market == 'hk':
                df = fn(stock=c.zfill(5), symbol=symbol, indicator=indicator)
            else:
                df = fn(stock=c, symbol=symbol, indicator=indicator)
        except Exception as e:
            return {'ok': False, 'msg': f'{market} 财报获取失败: {e}', 'df': None}
        if df is None or df.empty:
            return {'ok': True, 'rows': [], 'msg': '无财报数据', 'df': None}
        return {'ok': True, 'rows': df.to_dict('records'), 'df': df}

    # ---------- 公司公告 / 新闻 ----------
    def news(self, code, market='hk', limit=20):
        """公司公告与新闻。港股：东财港股新闻；美股：东财美股新闻。

        当前预留：akshare 暂无统一港美股新闻接口，使用东财快讯作为兜底。
        """
        out = []
        try:
            if market == 'hk':
                fn = getattr(ak, 'stock_hk_news' if hasattr(ak, 'stock_hk_news')
                            else 'stock_news_em', None)
                if fn is not None:
                    try:
                        df = fn(symbol=str(code).zfill(5)) if market == 'hk' \
                            else None
                    except Exception:
                        df = None
                    if df is not None and not df.empty:
                        out = df.head(limit).to_dict('records')
        except Exception:
            out = []
        return {'ok': True, 'rows': out, 'market': market, 'code': str(code)}

    # ---------- 公司资料 ----------
    def profile(self, code, market='hk'):
        """公司概况。港股：stock_hk_company_profile_em。"""
        if ak is None:
            return {'ok': False, 'msg': 'akshare 未安装'}
        fn = getattr(ak, 'stock_hk_company_profile_em', None)
        if market != 'hk' or fn is None:
            return {'ok': False, 'msg': f'{market} 公司概况接口未预留', 'rows': []}
        try:
            df = fn(symbol=str(code).zfill(5))
        except Exception as e:
            return {'ok': False, 'msg': str(e), 'rows': []}
        if df is None or df.empty:
            return {'ok': True, 'rows': [], 'msg': '无数据'}
        return {'ok': True, 'rows': df.to_dict('records'), 'df': df}

    # ---------- 估值指标 ----------
    def valuation(self, code, market='hk'):
        """估值指标（PE/PB/股息率等）。预留占位。"""
        if ak is None:
            return {'ok': False, 'msg': 'akshare 未安装'}
        if market == 'hk':
            fn = getattr(ak, 'stock_hk_valuation_baidu', None)
            if fn is not None:
                try:
                    df = fn(symbol=str(code).zfill(5))
                    if df is not None and not df.empty:
                        return {'ok': True, 'rows': df.to_dict('records'),
                                'df': df}
                except Exception as e:
                    return {'ok': False, 'msg': str(e)}
        return {'ok': False, 'msg': f'{market} 估值接口未预留', 'rows': []}


# ----------------------------------------------------------------------------
# 全球持仓 / 账户管理（预留，独立于 A 股 portfolio.pkl）
# ----------------------------------------------------------------------------
class GlobalPortfolio:
    """港美股观察仓 / 模拟仓 / 实盘仓 的统一容器。

    文件：global_portfolio.json（与 watchlist.json 同目录）。
    在用户未开通账户前，可记录"观察仓"，用于信息差 / AI 分析联动。
    """

    FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'global_portfolio.json')

    def __init__(self, filepath=None):
        self.filepath = filepath or self.FILE
        self._lock = threading.Lock()
        self.data = {
            'hk': {'account_opened': False, 'positions': [], 'cash': 0.0,
                    'currency': 'HKD'},
            'us': {'account_opened': False, 'positions': [], 'cash': 0.0,
                    'currency': 'USD'},
        }
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    if isinstance(raw, dict):
                        for m, v in raw.items():
                            if m in self.data and isinstance(v, dict):
                                self.data[m].update(v)
        except Exception:
            pass

    def _save(self):
        try:
            with self._lock:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[WARN] 保存全球持仓失败: {e}')

    def set_account_opened(self, market, opened, broker='', notes=''):
        if market not in self.data:
            return {'ok': False, 'msg': f'未知市场 {market}'}
        self.data[market]['account_opened'] = bool(opened)
        if broker:
            self.data[market]['broker'] = broker
        if notes:
            self.data[market]['notes'] = notes
        self._save()
        return {'ok': True, 'msg': f'{market} 账户状态: '
                                    + ('已开通' if opened else '未开通')}

    def add_position(self, market, code, name, volume, avg_price=0.0,
                     open_date='', currency=''):
        if market not in self.data:
            return {'ok': False, 'msg': f'未知市场 {market}'}
        rec = {'code': str(code).strip(), 'name': name or str(code),
               'volume': float(volume), 'avg_price': float(avg_price),
               'open_date': open_date or datetime.datetime.now().strftime('%Y-%m-%d'),
               'currency': currency or self.data[market].get('currency', ''),
               'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        self.data[market].setdefault('positions', []).append(rec)
        self._save()
        return {'ok': True, 'msg': f'已添加 {market} 观察仓 {code} {name}',
                'position': rec}

    def update_price(self, market, code, price):
        found = False
        for p in self.data.get(market, {}).get('positions', []):
            if p.get('code') == str(code):
                p['last_price'] = float(price)
                p['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                found = True
        if found:
            self._save()
        return {'ok': found, 'msg': f'{market} {code} 现价更新: '
                                    + ('成功' if found else '未找到')}

    def remove_position(self, market, code):
        pos = self.data.get(market, {}).get('positions', [])
        before = len(pos)
        self.data[market]['positions'] = [p for p in pos
                                          if p.get('code') != str(code)]
        if len(self.data[market]['positions']) != before:
            self._save()
            return {'ok': True, 'msg': f'已移除 {market} {code}'}
        return {'ok': False, 'msg': f'{market} {code} 不在持仓中'}

    def list(self, market=None):
        if market:
            return self.data.get(market, {'positions': []})
        return {m: self.data.get(m, {}) for m in self.data}

    def all_positions(self):
        out = []
        for m, v in self.data.items():
            for p in v.get('positions', []):
                p2 = dict(p)
                p2['market'] = m
                out.append(p2)
        return out

    def to_dict(self):
        return {'markets': {m: self.data.get(m, {}) for m in self.data}}


# ----------------------------------------------------------------------------
# 信息差引擎（与自选 / 关注板块强关联）
# ----------------------------------------------------------------------------
class InfoGapEngine:
    """每日财报 / 信息差引擎。

    设计目标：
    - 与"自选"和"关注板块"双向关联：
        * 输入：watchlist.all() + 关注的板块列表 + 关注的股票代码
        * 输出：每日聚合的"财报日历 + 重大公告 + 信息差评分"
    - 信息差评分：基于"事件重要性 × 预期偏离度 × 时间敏感度"。
    - 预留"推送钩子"：push_hook 是 callable，默认空，未来接微信 / 邮件 / 桌面通知。
    """

    PRIORITY = {'urgent': 3, 'high': 2, 'medium': 1, 'low': 0}

    def __init__(self, market_data=None, watchlist=None,
                 push_hook=None, out_dir=None):
        self.md = market_data or GlobalMarketData()
        self.wl = watchlist
        self.push_hook = push_hook or self._noop
        self.out_dir = out_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '信息差报告')
        os.makedirs(self.out_dir, exist_ok=True)

    @staticmethod
    def _noop(payload):
        # 预留：未来接 微信 / 邮件 / 桌面通知 / 系统托盘
        try:
            print(f'[InfoGap] 推送: {payload.get("title", "")}')
        except Exception:
            pass

    # ---------- 财报日历 ----------
    def earnings_calendar(self, date_str='', markets=('hk', 'us'),
                          codes=None):
        """财报日历。date_str: 'YYYY-MM-DD'，默认今天。

        当前实现：预留结构 + 返回空数据 + 说明。
        未来接入：akshare 无统一财报日历 API，需对接
          - 港交所披露易（HKEX）
          - SEC EDGAR（美股 10-K / 10-Q / 8-K）
          - 或第三方（如 Tushare Pro / Wind / 同花顺）
        返回统一结构，方便上层 UI 直接渲染。
        """
        date_str = date_str or datetime.date.today().isoformat()
        out = {
            'date': date_str,
            'markets': list(markets),
            'events': [],
            'source': 'reserved',
            'note': '财报日历数据源预留，开通账户后接入 HKEX / EDGAR / Tushare',
        }
        if codes:
            # 对每只自选股，查询最近一次财报
            for c in codes:
                for m in markets:
                    try:
                        rep = self.md.financial_report(c, market=m,
                                                       indicator='按季度')
                        if rep.get('ok') and rep.get('rows'):
                            last = rep['rows'][0]
                            out['events'].append({
                                'code': c, 'market': m,
                                'report_date': str(last.get('REPORT_DATE',
                                                       last.get('report_date', ''))),
                                'title': f'{m.upper()} 财报 {c}',
                                'priority': 'medium',
                                'payload': last,
                            })
                    except Exception:
                        pass
        return out

    # ---------- 重大公告 ----------
    def major_announcements(self, codes, markets=('hk', 'us'), limit=50):
        """重大公告。预留：拉取新闻 / 公告，按关键词打分。"""
        KEYWORDS = ['业绩', '财报', '亏损', '净利润', '指引', '回购',
                    '拆分', '合并', '收购', '诉讼', '监管', '停牌',
                    '复牌', '派息', '分红', '增发', '减持', '增持',
                    '董事', '辞任', '任命', 'CEO', 'CFO', 'CEO']
        out = []
        for c in codes:
            for m in markets:
                try:
                    res = self.md.news(c, market=m, limit=limit)
                    for row in res.get('rows', []):
                        text = str(row.get('title', '')) + \
                               str(row.get('content', ''))
                        hit = [k for k in KEYWORDS if k in text]
                        if hit:
                            priority = 'high' if len(hit) >= 2 else 'medium'
                            out.append({
                                'code': c, 'market': m,
                                'title': str(row.get('title', ''))[:80],
                                'priority': priority,
                                'keywords': hit,
                                'time': str(row.get('time',
                                                  row.get('pubTime', ''))),
                                'url': str(row.get('url', '')),
                            })
                except Exception:
                    continue
        # 按优先级 + 时间排序
        out.sort(key=lambda x: -self.PRIORITY.get(x['priority'], 0))
        return out[:limit]

    # ---------- 信息差评分 ----------
    def score_info_gap(self, code, market='hk', event_text='',
                       base_price=0.0, deviation_pct=0.0,
                       days_to_event=0):
        """单事件信息差评分 0-100。

        公式（预留，未来可调权重）：
          0.4 * 事件重要性 + 0.4 * 预期偏离度 + 0.2 * 时间敏感度
        """
        importance = 50
        dev_score = min(100, abs(float(deviation_pct or 0)) * 2)
        time_score = max(0, 100 - abs(int(days_to_event or 0)) * 10)
        total = importance * 0.4 + dev_score * 0.4 + time_score * 0.2
        return {
            'code': code, 'market': market,
            'total': round(total, 1),
            'importance': importance,
            'deviation': round(dev_score, 1),
            'time': round(time_score, 1),
            'base_price': base_price,
            'days_to_event': days_to_event,
        }

    # ---------- 每日聚合 ----------
    def daily_digest(self, watchlist_codes=None, sector_names=None,
                     push=True):
        """每日信息差 + 财报聚合。

        入参：
          watchlist_codes: 自选股代码列表（含港美股）
          sector_names: 关注的板块名称列表
        返回：
          dict 含 earnings / announcements / info_gap / push_result
        """
        watchlist_codes = watchlist_codes or []
        sector_names = sector_names or []

        # 1) 财报日历
        earnings = self.earnings_calendar(
            date_str=datetime.date.today().isoformat(),
            codes=watchlist_codes)

        # 2) 重大公告
        announcements = self.major_announcements(watchlist_codes)

        # 3) 信息差评分（对每条公告做粗评）
        scored = []
        for a in announcements:
            s = self.score_info_gap(
                code=a['code'], market=a['market'],
                event_text=a.get('title', ''),
                deviation_pct=0, days_to_event=0)
            s.update(a)
            scored.append(s)
        scored.sort(key=lambda x: -x['total'])

        digest = {
            'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'earnings': earnings,
            'announcements': scored[:20],
            'sectors_followed': list(sector_names),
            'watchlist_size': len(watchlist_codes),
        }

        # 4) 推送（预留钩子）
        push_result = {'ok': False, 'msg': '未启用推送钩子'}
        if push:
            try:
                self.push_hook({
                    'title': f'每日信息差 {digest["generated_at"]}',
                    'earnings_count': len(earnings.get('events', [])),
                    'announcements': digest['announcements'][:5],
                    'digest': digest,
                })
                push_result = {'ok': True, 'msg': '已调用推送钩子'}
            except Exception as e:
                push_result = {'ok': False, 'msg': str(e)}
        digest['push_result'] = push_result

        # 5) 落盘
        try:
            day = datetime.date.today().strftime('%Y%m%d')
            path = os.path.join(self.out_dir, f'信息差_{day}.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(digest, f, ensure_ascii=False, indent=2)
            digest['saved_to'] = path
        except Exception as e:
            digest['save_error'] = str(e)

        return digest


# ----------------------------------------------------------------------------
# 统一门面（供上层 Web / GUI 调用）
# ----------------------------------------------------------------------------
class GlobalSecuritiesFacade:
    """对外单一入口，聚合 行情 / 历史 / 财报 / 公告 / 持仓 / 信息差。"""

    def __init__(self, watchlist=None):
        self.registry = MarketRegistry()
        self.md = GlobalMarketData(self.registry)
        self.gp = GlobalPortfolio()
        self.eg = InfoGapEngine(market_data=self.md,
                                watchlist=watchlist,
                                out_dir=os.path.join(
                                    os.path.dirname(os.path.abspath(__file__)),
                                    '..', '信息差报告'))

    # ---- 市场状态 ----
    def markets(self):
        return self.registry.list()

    def market_status(self, market='hk'):
        info = self.registry.get(market)
        if info is None:
            return {'ok': False, 'msg': f'未知市场 {market}'}
        d = info.to_dict()
        d['account_opened'] = self.gp.data.get(market, {}).get(
            'account_opened', info.account_opened)
        return {'ok': True, **d}

    def set_account_opened(self, market, opened, broker='', notes=''):
        return self.gp.set_account_opened(market, opened,
                                          broker=broker, notes=notes)

    # ---- 行情 / 历史 ----
    def realtime(self, codes, market='hk'):
        return self.md.realtime(codes, market=market)

    def history(self, code, market='hk', years=2):
        return self.md.history(code, market=market, years=years)

    def financial_report(self, code, market='hk'):
        return self.md.financial_report(code, market=market)

    def news(self, code, market='hk'):
        return self.md.news(code, market=market)

    # ---- 持仓 ----
    def positions(self, market=None):
        return self.gp.list(market)

    def add_position(self, market, code, name, volume, avg_price=0.0):
        return self.gp.add_position(market, code, name, volume,
                                    avg_price=avg_price)

    def remove_position(self, market, code):
        return self.gp.remove_position(market, code)

    # ---- 信息差 ----
    def daily_digest(self, watchlist_codes=None, sector_names=None,
                     push=True):
        return self.eg.daily_digest(watchlist_codes=watchlist_codes,
                                    sector_names=sector_names,
                                    push=push)


# ----------------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------------
def _demo():
    facade = GlobalSecuritiesFacade()
    print('市场列表:')
    for m in facade.markets():
        print(' ', m['market'], m['name'],
              '已开通' if m['account_opened'] else '未开通',
              '数据已接入' if m['data_ready'] else '数据未接入')
    print('港股状态:', facade.market_status('hk'))
    print('美股状态:', facade.market_status('us'))
    print('港股行情(腾讯00700):',
          facade.realtime(['00700'], market='hk')['rows'][:1])
    print('持仓(未添加):', facade.positions('hk'))
    r = facade.add_position('hk', '00700', '腾讯控股', 1000, avg_price=350)
    print('添加观察仓:', r['msg'])
    print('当前持仓:', facade.positions('hk'))


if __name__ == '__main__':
    _demo()
