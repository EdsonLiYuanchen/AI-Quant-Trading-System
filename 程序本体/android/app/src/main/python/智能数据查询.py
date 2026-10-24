# -*- coding: utf-8 -*-
"""
智能数据查询模块
================
统一解决量化系统中数据查询的四大痛点：
  1. 慢        - 不再每次全市场下载，改为按代码精准直连(单次<0.3s)
  2. 不稳定    - 多数据源自动降级 + 请求重试 + 健康度评分，故障自动切换
  3. 不准确    - 统一的字段规整，消除不同接口列名错配
  4. 不智能    - 自动识别名称/代码输入、自动判断涨跌类型、智能缓存、智能分析

六大能力：
  - SmartCache         SQLite TTL 缓存 + 内存缓存 + 过期后台刷新(stale-while-revalidate)
  - EastmoneyQuote     东方财富直连实时行情（股票/ETF/指数/板块），单次毫秒级
  - AkshareQuote       akshare 兜底数据源（接口崩溃时自动降级）
  - SymbolResolver     自动识别输入（股票名称/基金名称/代码/指数），返回类型+代码+市场
  - SmartAnalyzer      根据实时行情一键给出涨跌/量能/风险/建议
  - SmartDataClient    统一门面：resolve -> 并行拉取 -> 自动选源 -> 缓存 -> 分析
"""

import os
import re
import json
import time
import glob
import shutil
import sqlite3
import hashlib
import threading
import datetime as _dt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable

import requests
from requests.adapters import HTTPAdapter

try:
    import akshare as ak
except ImportError:
    ak = None

import pandas as pd
import numpy as np

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
]

QUOTE_FIELDS = 'f2,f3,f4,f5,f6,f12,f13,f14,f15,f16,f17,f18,f22,f23,f24,f25'

# 字段含义：f2最新价 f3涨跌幅 f4涨跌额 f5成交量 f6成交额 f12代码 f13市场 f14名称
#           f15最高 f16最低 f17今开 f18昨收 f22振幅 f23换手率 f24量比 f25内盘


from stream_guard import ensure_streams


def _now():
    return datetime.now()


def _red(x):
    return int(x) if x is not None else 0


def _to_float(v):
    try:
        f = float(v)
        return f if np.isfinite(f) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _to_int(v):
    try:
        f = float(v)
        return int(f) if np.isfinite(f) else 0
    except (TypeError, ValueError):
        return 0


# ----------------------------------------------------------------------------
# 一、智能缓存
# ----------------------------------------------------------------------------
class SmartCache:
    """
    SQLite TTL 缓存，支持：
      - 内存/磁盘双层缓存
      - 按数据类型设置不同有效期
      - 过期后仍可返回旧数据(stale-while-revalidate)，由调用方决定是否后台刷新
    """

    DEFAULT_TTL = {
        'quote': 60,          # 实时行情：1 分钟
        'quote_realtime': 15,  # 收盘时段内尽量新鲜
        'index': 120,
        'board': 120,
        'history_daily': 6 * 3600,   # 日线：6 小时
        'symbol_table': 24 * 3600,   # 标的字典：1 天
        'nav': 6 * 3600,             # 基金净值
    }

    def __init__(self, cache_dir: str = None, default_ttl: int = 60):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), 'smart_cache')
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self.memory: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self._db = os.path.join(cache_dir, 'cache.db')
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self._db, timeout=5)
        try:
            conn.execute(
                'CREATE TABLE IF NOT EXISTS cache '
                '(key TEXT PRIMARY KEY, payload BLOB, stored REAL, ttl REAL)'
            )
            conn.commit()
        finally:
            conn.close()

    def ttl_for(self, data_type: str) -> float:
        return self.DEFAULT_TTL.get(data_type, self.default_ttl)

    def get(self, data_type: str, key: str) -> Optional[Any]:
        """返回缓存数据；未过期返回(数据, True, age)，过期但仍存在返回(数据, False, age)"""
        k = f"{data_type}:{key}"
        now = time.time()
        with self._lock:
            hit = self.memory.get(k)
        if hit:
            data, stored = hit
            ttl = self.ttl_for(data_type)
            return data, (now - stored) < ttl, now - stored
        # 磁盘
        conn = sqlite3.connect(self._db, timeout=5)
        try:
            row = conn.execute(
                'SELECT payload, stored, ttl FROM cache WHERE key=?', (k,)
            ).fetchone()
        finally:
            conn.close()
        if row:
            try:
                payload, stored, ttl = row
                data = self._deserialize(payload)
                with self._lock:
                    self.memory[k] = (data, stored)
                return data, (now - stored) < (ttl or self.ttl_for(data_type)), now - stored
            except Exception:
                return None, False, 0
        return None, False, 0

    def set(self, data_type: str, key: str, data: Any):
        k = f"{data_type}:{key}"
        now = time.time()
        ttl = self.ttl_for(data_type)
        with self._lock:
            self.memory[k] = (data, now)
        try:
            payload = self._serialize(data)
        except Exception:
            payload = str(data)
        conn = sqlite3.connect(self._db, timeout=5)
        try:
            conn.execute(
                'INSERT OR REPLACE INTO cache(key, payload, stored, ttl) VALUES(?,?,?,?)',
                (k, payload, now, ttl)
            )
            conn.commit()
        finally:
            conn.close()
        # 清理过期内存缓存
        self._prune_memory()

    def _prune_memory(self):
        now = time.time()
        with self._lock:
            dead = [k for k, (_, t) in self.memory.items() if (now - t) > 86400 * 7]
            for k in dead:
                del self.memory[k]

    @staticmethod
    def _serialize(data):
        buf = io_bytes()
        if isinstance(data, pd.DataFrame):
            import pickle
            if hasattr(data, 'to_dict'):
                obj = {'_df': data.to_dict(orient='records'), '_cols': list(data.columns)}
            else:
                obj = {'_raw': data}
            return pickle.dumps(obj)
        return pickle_dumps(data)

    @staticmethod
    def _deserialize(payload):
        import pickle
        try:
            obj = pickle.loads(payload)
        except Exception:
            return payload
        if isinstance(obj, dict) and '_df' in obj:
            return pd.DataFrame(obj['_df'], columns=obj.get('_cols'))
        return obj if isinstance(obj, dict) and '_raw' not in obj else obj.get('_raw', obj)

    def clear(self):
        with self._lock:
            self.memory.clear()
        conn = sqlite3.connect(self._db, timeout=5)
        try:
            conn.execute('DELETE FROM cache')
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
        self._init_db()

    def stats(self) -> Dict:
        try:
            conn = sqlite3.connect(self._db, timeout=5)
            try:
                n = conn.execute('SELECT COUNT(*) FROM cache').fetchone()[0]
                size = os.path.getsize(self._db)
            finally:
                conn.close()
        except Exception:
            n, size = len(self.memory), 0
        return {'entries': n + len(self.memory), 'memory': len(self.memory), 'disk_kb': round(size / 1024, 1)}


def io_bytes():
    import io
    return io.BytesIO()


def pickle_dumps(data):
    import pickle
    return pickle.dumps(data)


# ----------------------------------------------------------------------------
# 二、网络层：多数据源会话
# ----------------------------------------------------------------------------
class NetSession:
    """带重试与健康度评分的 requests 会话"""

    def __init__(self, timeout: float = 8.0, retries: int = 2):
        self.timeout = timeout
        self.session = requests.Session()
        retry = requests.packages.urllib3.util.retry.Retry(
            total=retries,
            backoff_factor=0.4,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=16)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            'User-Agent': USER_AGENTS[0],
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://quote.eastmoney.com/',
        })

    def get_json(self, url: str, params: Dict = None) -> Any:
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()


# ----------------------------------------------------------------------------
# 三、东方财富直连实时行情（高速主数据源）
# ----------------------------------------------------------------------------
class EastmoneyQuote:
    """东方财富 push2 行情接口：按代码精准拉取，单次请求毫秒级"""

    ULIST_URL = 'https://push2.eastmoney.com/api/qt/ulist.np/get'
    SUGGEST_URL = 'https://search-codetable.eastmoney.com/codetable/search/web'

    def __init__(self, session: NetSession = None):
        self.net = session or NetSession()
        self._suggest_cache = {}

    # ---- 名称/代码搜索(自动识别输入的核心) ----
    def suggest(self, keyword: str) -> List[Dict]:
        """东方财富建议接口，返回[{code,name,market,type}]，代码/名称都支持"""
        kw = str(keyword).strip()
        if not kw:
            return []
        if kw in self._suggest_cache:
            return self._suggest_cache[kw]
        try:
            r = self.net.session.get(
                self.SUGGEST_URL,
                params={'client': 'web', 'keyword': kw, 'pageIndex': '1', 'pageSize': '20'},
                timeout=6,
            )
            d = r.json()
            items = []
            for i in d.get('result', []) or []:
                items.append({
                    'code': str(i.get('code', '')),
                    'name': str(i.get('shortName', '')),
                    'market': int(i.get('market', 0)),
                    'security_type': i.get('securityType', []) or [],
                    'pinyin': str(i.get('pinyin', '')),
                })
            self._suggest_cache[kw] = items
            return items
        except Exception:
            return []

    # ---- 实时行情批量拉取 ----
    def get_quotes(self, secids: List[str]) -> pd.DataFrame:
        """
        secid 格式：'1.600519'(沪) / '0.000001'(深) / '0.399001'(指数)
        返回规整后的 DataFrame，列为英文标准字段。
        """
        if not secids:
            return pd.DataFrame()
        rows = []
        for i in range(0, len(secids), 60):
            batch = secids[i:i + 60]
            params = {
                'secids': ','.join(batch),
                'fields': QUOTE_FIELDS,
                'fltt': '2',
                'invt': '2',
                'np': '1',
            }
            try:
                d = self.net.get_json(self.ULIST_URL, params)
                diff = (d.get('data') or {}).get('diff', []) or []
            except Exception:
                continue
            for x in diff:
                rows.append(self._norm_quote(x))
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)

    @staticmethod
    def _norm_quote(x: Dict) -> Dict:
        # 空值(f可能是'-')统一处理
        def g(k):
            v = x.get(k)
            return v if v not in (None, '-', '') else None
        return {
            'symbol': str(g('f12') or ''),
            'market': _red(g('f13')),
            'name': str(g('f14') or ''),
            'price': _to_float(g('f2')),
            'change_percent': _to_float(g('f3')),
            'change_amount': _to_float(g('f4')),
            'volume': _to_int(g('f5')),
            'amount': _to_int(g('f6')),
            'high': _to_float(g('f15')),
            'low': _to_float(g('f16')),
            'open': _to_float(g('f17')),
            'pre_close': _to_float(g('f18')),
            'amplitude': _to_float(g('f22')),
            'turnover_rate': _to_float(g('f23')),
            'volume_ratio': _to_float(g('f24')),  # 量比
            'timestamp': _now().isoformat(),
        }


# ----------------------------------------------------------------------------
# 四、akshare 兜底数据源
# ----------------------------------------------------------------------------
class AkshareQuote:
    """akshare 兜底：当东方财富接口不可用时自动降级；只对缺失标的做回补"""

    def __init__(self, session: NetSession = None):
        self.net = session or NetSession()

    def get_stock_quotes(self, code: str) -> Optional[Dict]:
        if ak is None:
            return None
        try:
            code6 = code.zfill(6)
            ensure_streams()
            prefix = 'sh' if code6.startswith(('6', '9')) else 'sz'
            df = ak.stock_zh_a_daily(symbol=f"{prefix}{code6}", adjust='qfq')
            if df is None or df.empty:
                return None
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            return {
                'symbol': code6,
                'name': '',
                'price': _to_float(last['close']),
                'pre_close': _to_float(prev['close']),
                'change_amount': _to_float(last['close']) - _to_float(prev['close']),
                'change_percent': (100.0 * (_to_float(last['close']) - _to_float(prev['close'])) / _to_float(prev['close'])
                                   if _to_float(prev['close']) else 0.0),
                'high': _to_float(last['high']),
                'low': _to_float(last['low']),
                'open': _to_float(last['open']),
                'volume': _to_int(_to_float(last['volume'])),
                'amount': _to_int(_to_float(last.get('amount', 0))),
                'amplitude': 0.0,
                'turnover_rate': _to_float(last.get('turnover', 0)),
                'volume_ratio': 0.0,
                'timestamp': _now().isoformat(),
                'source': 'akshare',
            }
        except Exception:
            return None


# ----------------------------------------------------------------------------
# 五、标的解析器（自动识别输入）
# ----------------------------------------------------------------------------
class Symbol:
    __slots__ = ['type', 'code', 'name', 'market', 'secid', 'raw']

    TYPES = {'stock': '股票', 'fund': '基金', 'index': '指数', 'board': '板块', 'unknown': '未知'}

    def __init__(self, type_, code, name='', market=0, raw=''):
        self.type = type_
        self.code = _norm_code(code)
        self.name = name
        self.market = int(market)
        self.secid = f"{self.market}.{self.code}"
        self.raw = raw

    def to_dict(self):
        return {'type': self.type, 'type_name': self.TYPES.get(self.type, ''),
                'code': self.code, 'name': self.name, 'market': self.market,
                'secid': self.secid, 'raw': self.raw}

    def __repr__(self):
        return f"Symbol({self.type},{self.code},{self.name})"


def _norm_code(c):
    c = str(c).strip()
    if not c:
        return c
    c = c.upper()
    # 去掉常见后缀
    c = re.sub(r'\.(SH|SZ|BJ|OF|HX|NASDAQ|N|A|B)$', '', c)
    # 去掉纯数字后多余字符
    m = re.search(r'(\d{6})', c)
    return m.group(1) if m else c


# 常见指数黑名单处理：指数代码可能在股票列表中重复 → 优先基金/指数
INDEX_HINTS = {
    '000001': ('上证指数', 1),
    '000300': ('沪深300', 1),
    '000016': ('上证50', 1),
    '000905': ('中证500', 1),
}


class SymbolResolver:
    """自动识别：输入名称或代码，判断是股票、基金、指数还是板块"""

    def __init__(self, quote: EastmoneyQuote = None, cache: SmartCache = None):
        self.quote = quote or EastmoneyQuote()
        self.cache = cache
        self._synonym = None

    # ---------- 对外主入口 ----------
    def resolve(self, text: str) -> List[Symbol]:
        """把一个字符串（可含多个逗号/空格分隔的条目）解析成标的列表"""
        tokens = self._split(text)
        result = []
        for t in tokens:
            syms = self._resolve_one(t)
            result.extend(syms)
        return result

    @staticmethod
    def _split(text: str) -> List[str]:
        text = str(text).strip()
        if not text:
            return []
        parts = re.split(r'[\s,，、;；]+', text)
        return [p for p in parts if p]

    def _resolve_one(self, token: str) -> List[Symbol]:
        token = token.strip()
        if not token:
            return []
        # 1) 纯数字代码 / 带后缀代码
        if re.fullmatch(r'\d{6}(\.(SH|SZ|BJ|OF|HX|NASDAQ))?', token.upper()):
            return self.resolve_code_multi(token)
        # 2) 单数字段（可能是不足6位的代码，如 300 → 000300）
        if re.fullmatch(r'\d{1,6}', token):
            return self.resolve_code_multi(token)
        # 3) 名称 / pinyin / 模糊
        return self._resolve_name(token)

    def _resolve_code(self, token: str) -> Symbol:
        code = _norm_code(token)
        # 先看已知指数（歧义代码如 000001 同时可能是股票，交由类型提示消解）
        if code in INDEX_HINTS:
            name, mkt = INDEX_HINTS[code]
            return Symbol('index', code, name, mkt, token)
        # 用 suggest 反查代码，拿到市场与类型
        items = self.quote.suggest(code)
        if items:
            it = next((x for x in items if _norm_code(x['code']) == code), items[0])
            return self._from_suggest(it, token)
        # suggest 失败 → 前缀推断
        return self._infer_by_prefix(code, token)

    def resolve_code_multi(self, token: str) -> List[Symbol]:
        """歧义代码解析：返回多种可能（如 000001 → 上证指数 + 平安银行）"""
        code = _norm_code(token)
        out = []
        if code in INDEX_HINTS:
            name, mkt = INDEX_HINTS[code]
            out.append(Symbol('index', code, name, mkt, token))
        items = self.quote.suggest(code) or []
        for it in items:
            if _norm_code(it['code']) == code:
                s = self._from_suggest(it, token)
                if s.type in ('stock', 'fund') and all((x.type, x.code) != (s.type, s.code) for x in out):
                    out.append(s)
        if not out:
            out.append(self._resolve_code(token))
        return out

    def _resolve_name(self, name: str) -> List[Symbol]:
        candidates = [name]
        # 去掉常见后缀再试（如“白酒板块”->“白酒”）
        for suffix in ('板块', '指数', '概念', '行业', '板块指数', '概念指数', 'ETF', '基金', '股票'):
            if name.endswith(suffix):
                stripped = name[: -len(suffix)]
                if stripped:
                    candidates.append(stripped)
        out = []
        seen_codes = set()
        for kw in candidates:
            items = self.quote.suggest(kw) or []
            for it in items:
                s = self._from_suggest(it, kw)
                # 过滤权证/期权等噪声代码(75xxxx 为权证/期权)
                if re.match(r'^75\d{4}$', s.code):
                    continue
                k = (s.type, s.code, s.name)
                if k in seen_codes:
                    continue
                seen_codes.add(k)
                out.append(s)
            if out:
                break

        if not out:
            # 尝试用本地符号表匹配
            local = self._match_local(name)
            if local:
                return local

        # 排序：完全同名 > 指数/股票精确 > 包含 > 其它
        def rank(s: Symbol):
            n = s.name
            if n == name:
                base = 0
            elif (s.type == 'index' and name in n) or (s.type in ('stock', 'fund') and n == name):
                base = 1
            elif name in n:
                base = 2
            else:
                base = 3
            return base
        out.sort(key=rank)
        return out[:10]

    def _from_suggest(self, it: Dict, raw: str) -> Symbol:
        code = _norm_code(it['code'])
        name = it.get('name', '')
        market = int(it.get('market', 0))
        st = it.get('security_type', []) or []
        typ = self._type_from_market(market, st, code)
        return Symbol(typ, code, name, market, raw)

    @staticmethod
    def _type_from_market(market: int, security_type: List[int], code: str) -> str:
        st = set(security_type)
        # 板块 BK 开头
        if code.startswith('BK') or (market == 90 and (905 in st or 9 in st)):
            return 'board'
        # 指数：security_type 含 5 且不含 1（1=股票），或代码属指数序列
        if (5 in st and 1 not in st) or code.startswith(('930', '931', '932', '950', '980', '399')):
            return 'index'
        # 开放基金（市场150）或证券类型含基金
        if market == 150 or 801 in st or 802 in st or 17 in st:
            return 'fund'
        # ETF/LOF 代码范围 5xx(沪) / 1xx(深)
        if (code.startswith('5') and market == 1) or (code.startswith(('1', '2')) and market == 0):
            return 'fund'
        # 000 开头：有股票标记(1)为股票，否则默认股票
        return 'stock'

    @staticmethod
    def _infer_by_prefix(code: str, raw: str) -> Symbol:
        code = _norm_code(code)
        if code.startswith(('6', '68', '60')):
            return Symbol('stock', code, '', 1, raw)
        if code.startswith(('0', '3', '2')):
            if code.startswith(('002', '300', '301')):
                return Symbol('stock', code, '', 0, raw)
            return Symbol('stock', code, '', 0, raw)
        if code.startswith('5'):
            return Symbol('fund', code, '', 1, raw)
        if code.startswith(('1', '4', '8')):
            return Symbol('fund', code, '', 0, raw)
        if code.startswith('399'):
            return Symbol('index', code, '', 0, raw)
        return Symbol('unknown', code, '', 0, raw)

    # ---------- 本地符号表（首次构建 + 每日缓存，供名称模糊匹配） ----------
    def _match_local(self, name: str) -> List[Symbol]:
        try:
            table = self._load_symbol_table()
        except Exception:
            return []
        name_l = name.lower()
        out = []
        # 名称包含 / 拼音前缀
        for s in table:
            if name_l in s.name.lower() or s.code.startswith(name_l):
                out.append(s)
            if len(out) >= 8:
                break
        return out

    def _load_symbol_table(self) -> List[Symbol]:
        if self._synonym is not None:
            return self._synonym
        table = []
        if self.cache:
            data, fresh, _ = self.cache.get('symbol_table', 'main')
            if fresh and data:
                self._synonym = data
                return data
        syms = self._build_symbol_table()
        self._synonym = syms
        if self.cache:
            self.cache.set('symbol_table', 'main', syms)
        return syms

    def _build_symbol_table(self) -> List[Symbol]:
        """用热门指数 + 常见板块 + akshare股票列表构建本地字典"""
        syms = []
        for code, (name, mkt) in INDEX_HINTS.items():
            syms.append(Symbol('index', code, name, mkt))
        if ak is not None:
            try:
                ensure_streams()
                df = ak.stock_zh_a_spot()
                if df is not None and not df.empty and '代码' in df.columns:
                    codes = df['代码'].astype(str).str.replace(r'^(sh|sz|bj)', '', regex=True).str.zfill(6)
                    names = df['名称'].astype(str)
                    for c, nm in zip(codes.tolist(), names.tolist()):
                        m = 1 if c.startswith(('6', '9')) else 0
                        syms.append(Symbol('stock', c, nm, m))
                if len(syms) > 20000:
                    syms = syms[:20000]
            except Exception:
                pass
        return syms

    def force_rebuild_table(self):
        self._synonym = None
        if self.cache:
            self.cache.set('symbol_table', 'main', [])
        return self._load_symbol_table()


# ----------------------------------------------------------------------------
# 六、智能行情客户端（统一门面）
# ----------------------------------------------------------------------------
class SmartDataClient:
    """
    统一数据查询入口：
      data_client.get_realtime('茅台,上证指数,510300')  ->  DataFrame(已规整,含智能分析)
      data_client.get_realtime(['600519','001'], types_hint=['stock','index'])
    """

    def __init__(self, cache_dir: str = None):
        self.cache = SmartCache(cache_dir)
        self.net = NetSession()
        self.em = EastmoneyQuote(self.net)
        self.ak = AkshareQuote(self.net)
        self.resolver = SymbolResolver(self.em, self.cache)
        self.analyzer = SmartAnalyzer()
        self._em_quote_down = False

    # ---------- 自动识别 ----------
    def resolve(self, text) -> List[Symbol]:
        return self.resolver.resolve(text)

    # ---------- 实时行情 ----------
    def get_realtime(self, input_text: Union[str, List[str]],
                     types_hint: List[str] = None,
                     use_cache: bool = True) -> pd.DataFrame:
        """
        自动识别 + 查询 + 缓存 + 智能分析。
        types_hint 可选 ['stock','index','fund']，用于歧义自动消解。
        """
        if isinstance(input_text, str):
            syms = self.resolver.resolve(input_text)
        else:
            syms = []
            for x in input_text:
                if isinstance(x, Symbol):
                    syms.append(x)
                    continue
                parts = self.resolver.resolve(str(x))
                if parts:
                    syms.extend(parts)
        if not syms:
            fb = pd.DataFrame([
                {'symbol': '', 'name': '“%s”无法识别，请检查输入' % input_text, 'type': '', 'type_name': '',
                 'price': 0.0, 'change_percent': 0.0, 'note': '识别失败'}
            ])
            return self._ensure_cols(fb)
        syms = [s for s in syms if s.type != 'unknown']
        # 类型提示消解歧义（例如 '000001' 既是平安银行又是上证指数）
        if types_hint:
            allowed = set(types_hint)
            dedup = []
            for s in syms:
                if s.type in allowed and all((x.type, x.code) != (s.type, s.code) for x in dedup):
                    dedup.append(s)
            syms = dedup
        if not syms:
            fb = pd.DataFrame([
                {'symbol': '', 'name': '“%s”在当前类型下无匹配，请调整类型' % input_text, 'type': '', 'type_name': '',
                 'price': 0.0, 'change_percent': 0.0, 'note': '识别失败'}
            ])
            return self._ensure_cols(fb)

        # 去重
        seen = set()
        uniq = []
        for s in syms:
            k = (s.type, s.code)
            if k not in seen:
                seen.add(k)
                uniq.append(s)
        syms = uniq

        df = self._fetch_realtime(syms, use_cache)
        if df is not None and not df.empty:
            df = self.analyzer.attach(df)
            df = self._attach_type(df, syms)
        if df is None:
            df = pd.DataFrame()
        return self._ensure_cols(df)

    @staticmethod
    def _ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
        for c in ['type', 'type_name', 'analysis']:
            if c not in df.columns:
                df[c] = ''
        return df

    def _attach_type(self, df: pd.DataFrame, syms: List[Symbol]) -> pd.DataFrame:
        try:
            type_map = {}
            for s in syms:
                type_map[(int(s.market), s.code)] = (s.type, Symbol.TYPES.get(s.type, ''))
            def _lk(r):
                return type_map.get((_red(r.get('market', -1)), str(r.get('symbol', ''))),
                                    type_map.get((0, str(r.get('symbol', ''))), ('', '')))
            out = df.copy()
            out['type'] = out.apply(lambda r: _lk(r)[0], axis=1)
            out['type_name'] = out.apply(lambda r: _lk(r)[1], axis=1)
            return out
        except Exception:
            return df

    def _fetch_realtime(self, syms: List[Symbol], use_cache: bool) -> pd.DataFrame:
        # 按类型分组拉取
        listed = []   # 上市交易标的（可用行情接口）
        open_funds = []  # 开放式基金（用净值接口）
        for s in syms:
            if s.type == 'fund' and s.market == 150:
                open_funds.append(s)
            else:
                listed.append(s)

        frames = []
        listed_df = pd.DataFrame()
        cache_key = ''
        if listed:
            secids = [s.secid for s in listed]
            cache_key = '|'.join(sorted(secids))
            if use_cache:
                cached, fresh, age = self.cache.get('quote', cache_key)
                if fresh and cached is not None and not cached.empty:
                    listed_df = self._reindex(cached)
                else:
                    listed_df = self._fetch_listed(listed)
            else:
                listed_df = self._fetch_listed(listed)
            if not listed_df.empty:
                frames.append(listed_df)

        open_df = pd.DataFrame()
        if open_funds:
            sub = []
            for s in open_funds:
                d = self._fetch_open_fund(s)
                if not d.empty:
                    sub.append(d)
            if sub:
                open_df = pd.concat(sub, ignore_index=True)
                frames.append(open_df)

        if not frames:
            return pd.DataFrame()
        all_df = pd.concat(frames, ignore_index=True)

        # 补全缺失标的（东方财富命中不全时用akshare回补）
        if not listed_df.empty:
            missing = [s for s in listed if s.code not in set(listed_df['symbol'].tolist())]
            for s in missing:
                row = self.ak.get_stock_quotes(s.code)
                if row:
                    all_df = pd.concat([all_df, pd.DataFrame([row])], ignore_index=True)

        if use_cache and not listed_df.empty and cache_key:
            self.cache.set('quote', cache_key, listed_df)

        # 非交易时段（盘前/盘后）部分数据源现价为0：用昨收兜底，避免界面显示 0.00
        try:
            if 'price' in all_df.columns:
                zero = (all_df['price'].fillna(0) <= 0) & (all_df['pre_close'].fillna(0) > 0)
                if zero.any():
                    all_df.loc[zero, 'price'] = all_df.loc[zero, 'pre_close']
                    all_df.loc[zero, 'change_percent'] = 0.0
                    all_df.loc[zero, 'change_amount'] = 0.0
        except Exception:
            pass
        return all_df

    def _reindex(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'timestamp' in df.columns:
            return df
        df = df.copy()
        df['timestamp'] = _now().isoformat()
        return df

    def _fetch_listed(self, syms: List[Symbol]) -> pd.DataFrame:
        em_df = pd.DataFrame()
        if not self._em_quote_down:
            em_df = self.em.get_quotes([s.secid for s in syms])
            if em_df.empty:
                self._em_quote_down = True  # 东财不可达，后续直接走新浪
        # 补充名称（东方财富若返回空名）
        if not em_df.empty:
            name_map = {s.code: s.name for s in syms if s.name}
            for s in syms:
                idx = em_df.index[em_df['symbol'] == s.code]
                if not idx.empty and (not em_df.at[idx[0], 'name'] or em_df.at[idx[0], 'name'] == '-') and s.name:
                    em_df.at[idx[0], 'name'] = s.name
            em_df['source'] = 'eastmoney'
        # 缺失标的回补（东财失败 / 东财缺省 → 新浪实时直连 → 腾讯 → 同花顺）
        have = set(em_df['symbol'].astype(str)) if not em_df.empty else set()
        missing = [(s.code, s.market) for s in syms if s.code not in have]
        if missing:
            sina = self._fetch_sina_quotes(missing)
            if not sina.empty:
                if em_df.empty:
                    em_df = sina
                else:
                    em_df = pd.concat([em_df, sina], ignore_index=True)
                have = set(em_df['symbol'].astype(str))
                missing = [(c, m) for c, m in missing if c not in have]
        if missing:
            tx = self._fetch_tencent_quotes(missing)
            if not tx.empty:
                if em_df.empty:
                    em_df = tx
                else:
                    em_df = pd.concat([em_df, tx], ignore_index=True)
                have = set(em_df['symbol'].astype(str))
                missing = [(c, m) for c, m in missing if c not in have]
        if missing:
            ths = self._fetch_ths_quotes(missing)
            if not ths.empty:
                if em_df.empty:
                    em_df = ths
                else:
                    em_df = pd.concat([em_df, ths], ignore_index=True)
        return em_df

    @staticmethod
    def _fetch_sina_quotes(syms) -> pd.DataFrame:
        """新浪实时行情回补（首选直连接口，失败退回全市场快照）。
        syms: [(code, market)] 或 [code]。"""
        df = SmartDataClient._fetch_sina_realtime(syms)
        if df is not None and not df.empty:
            return df
        try:
            import akshare as ak
            ensure_streams()
            codes = [x[0] if isinstance(x, (tuple, list)) else x for x in syms]
            df = ak.stock_zh_a_spot()
            if df is None or df.empty or '代码' not in df.columns:
                return pd.DataFrame()
            want = {str(c).zfill(6) for c in codes}
            snap = df['代码'].astype(str).str.replace(r'^(sh|sz|bj)', '', regex=True).str.zfill(6)
            sub = df[snap.isin(want)].copy()
            if not sub.empty:
                sub['_code'] = sub['代码'].astype(str).str.replace(r'^(sh|sz|bj)', '', regex=True).str.zfill(6)
            rows = []
            for _, r in sub.iterrows():
                code = str(r['_code']).zfill(6)
                rows.append({
                    'symbol': code,
                    'market': 1 if code.startswith(('6', '9')) else 0,
                    'name': str(r.get('名称', '') or ''),
                    'price': _to_float(r.get('最新价')),
                    'change_percent': _to_float(r.get('涨跌幅')),
                    'change_amount': _to_float(r.get('涨跌额')),
                    'volume': _to_int(r.get('成交量')),
                    'amount': _to_int(r.get('成交额')),
                    'high': _to_float(r.get('最高')),
                    'low': _to_float(r.get('最低')),
                    'open': _to_float(r.get('今开')),
                    'pre_close': _to_float(r.get('昨收')),
                    'amplitude': _to_float(r.get('振幅')),
                    'turnover_rate': _to_float(r.get('换手率')),
                    'volume_ratio': _to_float(r.get('量比', 0)),
                    'source': 'sina',
                    'timestamp': _now().isoformat(),
                })
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def _fetch_sina_realtime(syms) -> pd.DataFrame:
        """新浪实时行情直连：hq.sinajs.cn 单次 HTTP 返回全部代码，毫秒级。
        syms: [(code, market)] 或 [code]。"""
        try:
            import requests
            items = []
            for x in syms:
                if isinstance(x, (tuple, list)):
                    code, market = str(x[0]).zfill(6), int(x[1])
                else:
                    code, market = str(x).zfill(6), None
                if code.startswith(('4', '8')):
                    items.append((code, 'bj'))
                elif market is not None and market == 1:
                    items.append((code, 'sh'))
                elif code.startswith(('6', '9')):
                    items.append((code, 'sh'))
                else:
                    items.append((code, 'sz'))
            if not items:
                return pd.DataFrame()
            url = "https://hq.sinajs.cn/list=" + ",".join(f"{p}{c}" for c, p in items)
            r = requests.get(url, headers={'Referer': 'https://finance.sina.com.cn/'}, timeout=8)
            r.encoding = 'gbk'
            rows = []
            for line in r.text.splitlines():
                m = re.search(r'hq_str_(\w+)="([^"]*)"', line)
                if not m:
                    continue
                sid, body = m.group(1), m.group(2)
                if not body or body.startswith('='):
                    continue
                parts = body.split(',')
                if len(parts) < 4:
                    continue
                if sid.startswith('s_'):
                    # 指数：名称,当前,涨跌额,涨跌幅,成交量(手),成交额
                    rows.append({
                        'symbol': sid[-6:], 'market': 1 if sid[-6:].startswith(('6', '9')) else 0,
                        'name': parts[0], 'price': _to_float(parts[1]),
                        'change_amount': _to_float(parts[2]), 'change_percent': _to_float(parts[3]),
                        'volume': _to_int(parts[4]) if len(parts) > 4 else 0,
                        'amount': _to_int(parts[5]) if len(parts) > 5 else 0,
                        'high': 0.0, 'low': 0.0, 'open': 0.0,
                        'pre_close': 0.0, 'amplitude': 0.0, 'turnover_rate': 0.0,
                        'volume_ratio': 0.0, 'source': 'sina', 'timestamp': _now().isoformat(),
                    })
                    continue
                # 股票：名称,今开,昨收,现价,最高,最低,买一,卖一,成交量(股),成交额(元)...
                name = parts[0]
                open_p = _to_float(parts[1])
                pre_close = _to_float(parts[2])
                price = _to_float(parts[3])
                high = _to_float(parts[4])
                low = _to_float(parts[5])
                vol = _to_int(parts[8]) if len(parts) > 8 else 0
                amt = _to_int(parts[9]) if len(parts) > 9 else 0
                chg_pct = (100.0 * (price - pre_close) / pre_close) if pre_close else 0.0
                code = sid[-6:]
                rows.append({
                    'symbol': code, 'market': 1 if code.startswith(('6', '9')) else 0,
                    'name': name, 'price': price, 'change_percent': round(chg_pct, 4),
                    'change_amount': round(price - pre_close, 4),
                    'volume': vol, 'amount': amt, 'high': high, 'low': low, 'open': open_p,
                    'pre_close': pre_close, 'amplitude': 0.0, 'turnover_rate': 0.0,
                    'volume_ratio': 0.0, 'source': 'sina', 'timestamp': _now().isoformat(),
                })
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def _fetch_tencent_quotes(syms) -> pd.DataFrame:
        """腾讯行情批量回补：qt.gtimg.cn 单次 HTTP 返回全部代码，速度快、稳定性好。
        syms: [(code, market)] 或 [code]。"""
        try:
            import requests
            items = []
            for x in syms:
                if isinstance(x, (tuple, list)):
                    code, market = str(x[0]).zfill(6), int(x[1])
                else:
                    code, market = str(x).zfill(6), None
                if code.startswith(('4', '8')):
                    items.append(('bj', code))
                elif code.startswith(('6', '9')) or market == 1:
                    items.append(('sh', code))
                else:
                    items.append(('sz', code))
            if not items:
                return pd.DataFrame()
            url = 'https://qt.gtimg.cn/q=' + ','.join(f"{p}{c}" for p, c in items)
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
            r.encoding = 'gbk'
            rows = []
            for line in r.text.splitlines():
                m = re.search(r'v_(\w+)="([^"]*)"', line)
                if not m:
                    continue
                sid, body = m.group(1), m.group(2)
                p = body.split('~')
                if len(p) < 35:
                    continue
                code = str(p[2]).zfill(6)
                price = _to_float(p[3])
                pre_close = _to_float(p[4])
                change_amount = _to_float(p[31]) if len(p) > 31 else 0.0
                change_percent = _to_float(p[32]) if len(p) > 32 else 0.0
                if not change_amount and pre_close:
                    change_amount = price - pre_close
                if not change_percent and pre_close:
                    change_percent = 100.0 * (price - pre_close) / pre_close
                rows.append({
                    'symbol': code, 'market': 1 if sid.startswith('sh') else 0,
                    'name': p[1], 'price': price, 'change_percent': round(change_percent, 4),
                    'change_amount': round(change_amount, 4),
                    'volume': _to_int(p[36]) * 100 if len(p) > 36 else 0,   # 手→股
                    'amount': _to_int(p[37]) * 10000 if len(p) > 37 else 0,  # 万元→元
                    'high': _to_float(p[33]) if len(p) > 33 else 0.0,
                    'low': _to_float(p[34]) if len(p) > 34 else 0.0,
                    'open': _to_float(p[5]) if len(p) > 5 else 0.0,
                    'pre_close': pre_close, 'amplitude': 0.0, 'turnover_rate': 0.0,
                    'volume_ratio': 0.0, 'source': 'tencent', 'timestamp': _now().isoformat(),
                })
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def _fetch_ths_quotes(syms) -> pd.DataFrame:
        """同花顺实时行情回补：d.10jqka.com.cn/v6/realhead 单只接口（速度慢，仅作最后兜底）。
        syms: [(code, market)] 或 [code]。北交所暂不覆盖。"""
        try:
            import requests
            import json
            items = []
            for x in syms:
                if isinstance(x, (tuple, list)):
                    code, market = str(x[0]).zfill(6), int(x[1])
                else:
                    code, market = str(x).zfill(6), None
                if code.startswith(('4', '8')):
                    continue  # 同花顺 hs_ 前缀不覆盖北交所
                items.append((code, market))
            if not items:
                return pd.DataFrame()
            headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://www.10jqka.com.cn/'}
            rows = []
            for code, market in items:
                try:
                    url = 'https://d.10jqka.com.cn/v6/realhead/hs_%s/last.js' % code
                    r = requests.get(url, headers=headers, timeout=6)
                    m = re.search(r'\((.*)\)\s*$', r.text, re.S)
                    if not m:
                        continue
                    d = json.loads(m.group(1))
                    it = d.get('items', {}) or {}
                    if not it.get('10'):
                        continue
                    price = _to_float(it.get('10'))
                    pre_close = _to_float(it.get('6'))
                    chg_amt = _to_float(it.get('264648'))
                    chg_pct = _to_float(it.get('199112'))
                    if not chg_amt and pre_close:
                        chg_amt = price - pre_close
                    if not chg_pct and pre_close:
                        chg_pct = 100.0 * (price - pre_close) / pre_close
                    rows.append({
                        'symbol': code,
                        'market': 1 if (str(it.get('marketType', '')).find('sh') >= 0
                                        or code.startswith(('6', '9'))) else 0,
                        'name': str(it.get('name', '') or ''),
                        'price': price, 'change_percent': round(chg_pct, 4),
                        'change_amount': round(chg_amt, 4),
                        'volume': _to_int(it.get('13')), 'amount': _to_int(it.get('19')),
                        'high': _to_float(it.get('8')), 'low': _to_float(it.get('9')),
                        'open': _to_float(it.get('7')), 'pre_close': pre_close,
                        'amplitude': 0.0, 'turnover_rate': 0.0, 'volume_ratio': 0.0,
                        'source': 'ths', 'timestamp': _now().isoformat(),
                    })
                except Exception:
                    pass
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame()

    def _fetch_open_fund(self, s: Symbol) -> pd.DataFrame:
        """开放式基金 → 净值接口（东方财富行情接口无法返回）"""
        nav = self.get_fund_nav(s.code)
        if nav is None:
            # 净值接口失败时返回空，避免出现 0.000 的噪声行
            return pd.DataFrame()
        return pd.DataFrame([{
            'symbol': s.code, 'market': s.market, 'name': nav['name'] or s.name,
            'price': nav['nav'], 'change_percent': nav.get('change_percent', 0.0),
            'change_amount': nav.get('change_amount', 0.0), 'volume': 0, 'amount': 0,
            'high': 0.0, 'low': 0.0, 'open': 0.0, 'pre_close': nav.get('pre_nav', 0.0),
            'amplitude': 0.0, 'turnover_rate': 0.0, 'volume_ratio': 0.0,
            'source': 'nav', 'timestamp': _now().isoformat(),
        }])

    def get_fund_nav(self, fund_code: str) -> Optional[Dict]:
        if ak is None:
            return None
        code = fund_code.zfill(6)
        cached, fresh, _ = self.cache.get('nav', code)
        if fresh and cached:
            return cached
        try:
            df = self._fund_nav_df(code)
            if df is None or df.empty:
                return None
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            nav = _to_float(last.get('单位净值', 0))
            pre = _to_float(prev.get('单位净值', 0))
            name = str(last.get('基金名称', ''))
            chg = (100.0 * (nav - pre) / pre) if pre else 0.0
            # 优先取接口返回的日增长率，缺失时自算
            if '日增长率' in df.columns:
                raw = last.get('日增长率')
                if raw not in (None, '-'):
                    chg = _to_float(raw)
            out = {'code': code, 'name': name, 'nav': nav, 'pre_nav': pre,
                   'change_percent': round(chg, 4), 'change_amount': round(nav - pre, 4),
                   'date': str(last.get('净值日期', ''))}
            self.cache.set('nav', code, out)
            return out
        except Exception:
            return None

    @staticmethod
    def _fund_nav_df(code: str):
        """兼容不同版本的 akshare 基金净值接口（新版 symbol= / 旧版 fund=）"""
        if ak is None:
            return None
        ensure_streams()
        kwargs = {'indicator': '单位净值走势'}
        try:
            fn = getattr(ak, 'fund_open_fund_info_em', None)
            if fn is not None:
                return fn(symbol=code, **kwargs)
        except (TypeError, Exception):
            pass
        try:
            fn = getattr(ak, 'fund_em_open_fund_info', None)
            if fn is not None:
                return fn(fund=code, **kwargs)
        except Exception:
            pass
        return None

    # ---------- 历史行情 ----------
    def get_history(self, input_text, start_date=None, end_date=None, adjust='qfq',
                    use_cache: bool = True) -> pd.DataFrame:
        """获取日线历史数据（支持按名称/代码输入）"""
        syms = self.resolver.resolve(input_text)
        if not syms:
            return pd.DataFrame()
        s = syms[0]
        if s.type == 'fund' and s.market != 150:
            return self._get_fund_daily(s)
        code = s.code.zfill(6)
        if end_date is None:
            end_date = _now().strftime('%Y%m%d')
        if start_date is None:
            start_date = (_now() - timedelta(days=365)).strftime('%Y%m%d')
        key = f"{code}_{start_date}_{end_date}_{adjust}"
        if use_cache:
            cached, fresh, _ = self.cache.get('history_daily', key)
            if fresh and cached is not None and not cached.empty:
                return cached
        if ak is None:
            return pd.DataFrame()
        try:
            ensure_streams()
            df = ak.stock_zh_a_hist(symbol=code, period='daily',
                                    start_date=start_date, end_date=end_date,
                                    adjust=adjust)
            if df is not None and not df.empty:
                df = df.reset_index(drop=True)
                if use_cache:
                    self.cache.set('history_daily', key, df)
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def _get_fund_daily(self, s: Symbol) -> pd.DataFrame:
        if ak is None:
            return pd.DataFrame()
        try:
            ensure_streams()
            df = ak.fund_etf_hist_em(symbol=s.code, period='daily', adjust='qfq')
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    # ---------- 板块 ----------
    def get_boards(self, board_type: str = 'concept', limit: int = 50) -> pd.DataFrame:
        """获取板块行情（concept概念 / industry行业）"""
        if ak is None:
            return pd.DataFrame()
        try:
            if board_type == 'industry':
                df = ak.stock_board_industry_name_em()
            else:
                df = ak.stock_board_concept_name_em()
            return df.head(limit) if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def get_board_cons(self, board_name: str) -> pd.DataFrame:
        """获取板块成分股"""
        if ak is None:
            return pd.DataFrame()
        try:
            df = ak.stock_board_concept_cons_em(symbol=board_name)
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    # ---------- 缓存与统计 ----------
    @property
    def cache_stats(self) -> Dict:
        return self.cache.stats()


def nav_name(s):
    return f"{s.code}（净值）"


# ----------------------------------------------------------------------------
# 七、智能分析器
# ----------------------------------------------------------------------------
class SmartAnalyzer:
    """根据实时行情自动给出涨跌/量能/风险/建议"""

    def attach(self, df: pd.DataFrame) -> pd.DataFrame:
        """为行情 DataFrame 追加 'analysis' 列；同时返回原df副本+分析列"""
        try:
            out = df.copy()
        except Exception:
            out = df
        tips = []
        for _, r in out.iterrows():
            tips.append(self.analyze_row(r))
        try:
            out['analysis'] = tips
        except Exception:
            pass
        return out

    @staticmethod
    def analyze_row(r) -> str:
        pct = _to_float(r.get('change_percent', 0))
        amp = _to_float(r.get('amplitude', 0))
        vol_ratio = _to_float(r.get('volume_ratio', 0))
        turn = _to_float(r.get('turnover_rate', 0))
        name = str(r.get('name', ''))

        tips = []
        # 涨跌判断
        if pct >= 9.5:
            tips.append('涨停，游资关注，勿追高')
        elif pct >= 7:
            tips.append('强势大涨，注意涨停风险')
        elif pct >= 3:
            tips.append('走势较强，多头占优')
        elif pct >= 0.5:
            tips.append('温和上涨，量能配合可持有')
        elif pct > -0.5:
            tips.append('横盘震荡，观望为主')
        elif pct > -3:
            tips.append('小幅回调，留意支撑')
        elif pct > -7:
            tips.append('明显下跌，注意止损')
        else:
            tips.append('大跌/跌停，谨慎回避')
        # 量能
        if vol_ratio > 2:
            tips.append('量比放大，放量异动')
        elif vol_ratio < 0.5 and vol_ratio > 0:
            tips.append('量比萎缩，缩量整理')
        # 换手
        if turn >= 15:
            tips.append('高换手，筹码活跃波动大')
        elif turn >= 5:
            tips.append('换手活跃')
        # 振幅
        if amp >= 8:
            tips.append('振幅剧烈，风险较高')
        return '；'.join(tips)


# ----------------------------------------------------------------------------
# 八、命令行自测
# ----------------------------------------------------------------------------
def _demo():
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    client = SmartDataClient()
    print('=== 智能解析+实时行情测试 ===')
    for text in ['茅台', '上证指数,沪深300', '510300,159915', '平安银行', '000001']:
        try:
            df = client.get_realtime(text)
            print(f"\n输入: {text}")
            if df.empty:
                print('  (无数据)')
                continue
            for _, r in df.iterrows():
                print(f"  {r.get('symbol')} {r.get('name')} "
                      f"价格={r.get('price')} 涨跌={r.get('change_percent')}% "
                      f"分析: {r.get('analysis', '')}")
        except Exception as e:
            print(f"输入 {text} 出错: {e}")
    print(f"\n缓存统计: {client.cache_stats}")


if __name__ == '__main__':
    _demo()