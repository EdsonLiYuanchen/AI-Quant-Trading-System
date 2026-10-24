# -*- coding: utf-8 -*-
"""
AI 量化交易系统 · Web 前端版（pywebview）
=========================================
Python 只做数据获取、分析、决策；界面用 HTML/CSS/JS 渲染（现代美观）。

核心复用：
  - SmartDataClient   智能行情（多数据源自动降级 + 缓存）
  - LongTermAnalyzer  长线/短线榜单
  - Watchlist         自选股持久化
  - AutoTradingEngine + EasyTraderAPI  自动交易 / 真实下单
"""
import os
import sys
import json
import threading
import time

import pandas as pd  # noqa: E402

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# PyInstaller: ensure _MEIPASS is on sys.path so bundled webview/akshare can be found
_meipass = getattr(sys, "_MEIPASS", None)
if _meipass and _meipass not in sys.path:
    sys.path.insert(0, _meipass)

try:
    import webview  # noqa: E402  æ¡é¢ççªå£éè¦ï¼æ å¤´æå¡æ¨¡å¼（å®è£）ä¸ä¾èµ
    HAS_WEBVIEW = True
except ImportError:
    webview = None
    HAS_WEBVIEW = False

from 智能数据查询 import SmartDataClient  # noqa: E402
from 长线选股 import LongTermAnalyzer  # noqa: E402
from 自选股 import Watchlist  # noqa: E402
from 持仓管理 import PortfolioManager, FundManager  # noqa: E402

# AI混合策略：常态决策树 + 异动时切AI API深度分析
try:
    from ai_strategy import HybridAIStrategy  # noqa: E402
    HAS_HYBRID_AI = True
except Exception:
    HAS_HYBRID_AI = False


def resource_path(rel: str) -> str:
    base = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)


def _row_dicts(df):
    """DataFrame → JSON 可序列化的 dict 列表"""
    if df is None or df.empty:
        return []
    out = []
    for _, r in df.iterrows():
        d = {}
        for k, v in r.items():
            if hasattr(v, 'item'):
                try:
                    v = v.item()
                except Exception:
                    pass
            if isinstance(v, (float,)):
                if v != v:
                    v = None
            d[str(k)] = v
        out.append(d)
    return out


def _f(v, default=0.0):
    try:
        v = float(v)
        return v if v == v else default
    except (TypeError, ValueError):
        return default


def _is_true(v):
    """宽松布尔解析：True/'1'/'true'/'yes'/'on'/'是' 均视为真。"""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in ('1', 'true', 'yes', 'on', 'y', '是')


def _to_jsonable(obj):
    """把 pywebview 返回的数据递归转换为 JSON 可序列化的普通 Python 类型。"""
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        return obj if obj == obj else None
    if hasattr(obj, 'item'):
        try:
            return _to_jsonable(obj.item())
        except Exception:
            pass
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, pd.DataFrame):
        return _row_dicts(obj)
    if isinstance(obj, pd.Series):
        return _to_jsonable(obj.to_dict())
    import numpy as np
    if isinstance(obj, np.ndarray):
        return _to_jsonable(obj.tolist())
    if isinstance(obj, np.generic):
        return _to_jsonable(obj.item())
    import datetime
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return str(obj)
    try:
        import pandas as _pd
        if isinstance(obj, _pd.Timestamp):
            return str(obj)
    except Exception:
        pass
    return str(obj)


TRADING_CONFIG_FILE = 'trading_config.json'
ENGINE_STATE_FILE = 'engine_state.json'


def _load_engine_state():
    """读取引擎运行状态：{'auto_restart': bool, 'cfg': {...}, 'started_at': str}"""
    try:
        if os.path.exists(ENGINE_STATE_FILE):
            with open(ENGINE_STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _save_engine_state(state):
    """保存引擎运行状态（标记引擎是否需要自动续跑）"""
    try:
        with open(ENGINE_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _load_trading_config():
    """读取上次保存的全自动交易配置（股票池/参数等），文件与 watchlist.json 同目录（exe 目录）。"""
    try:
        if os.path.exists(TRADING_CONFIG_FILE):
            with open(TRADING_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _save_trading_config(cfg):
    """保存全自动交易配置，敏感字段（密码）不落盘。"""
    try:
        safe = {k: v for k, v in (cfg or {}).items() if k not in ('password',)}
        with open(TRADING_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(safe, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


class TradingController:
    """包装自动交易引擎，供前端启停/查状态。"""

    def __init__(self):
        self.engine = None
        self.lock = threading.Lock()
        self.logs = []
        self._snap_stop = threading.Event()
        # 自选 股 句柄（动态 选股 候选池 兜底 用；与 WebApi 共用 同一 份 watchlist.json）
        self._watch = None

    def _watch_handle(self):
        """懒加载 自选 股 句柄，避免 在 __init__ 时 强 依赖 文件 路径。"""
        if self._watch is None:
            try:
                from 自选股 import Watchlist
                self._watch = Watchlist()
            except Exception:
                class _Empty:
                    @staticmethod
                    def all():
                        return []
                self._watch = _Empty()
        return self._watch

    def _snapshot_loop(self, api):
        """引擎运行期间定期记录账户资产快照（用于收益视图，不影响交易逻辑）"""
        while not self._snap_stop.is_set():
            try:
                if hasattr(api, 'record_snapshot'):
                    api.record_snapshot()
            except Exception:
                pass
            self._snap_stop.wait(60)

    def _log(self, msg):
        self.logs.append(msg)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]

    def start(self, cfg: dict) -> dict:
        with self.lock:
            if self.engine is not None:
                return {'ok': False, 'msg': '引擎已在运行，请先停止'}
            try:
                from stock_trading_api import TradingAPIFactory, EasyTraderAPI
                from auto_trading_engine import AutoTradingEngine

                mode = str(cfg.get('mode', 'simulation')).strip().lower()
                if mode in ('simulation', 'simulated', 'mock', 'sim', '模拟'):
                    mode = 'simulated'
                if mode == 'easytrader' and not _is_true(cfg.get('allow_mock_strategy')):
                    return {'ok': False, 'msg': '自动交易当前使用随机模拟策略（MockAIStrategy），'
                                                 '真实账户会随机买卖。仅在下单通道测试时，'
                                                 '请勾选「允许用模拟策略实盘下单」后再启动。'}
                if mode == 'easytrader':
                    broker = str(cfg.get('broker', 'universal')).strip() or 'universal'
                    user = str(cfg.get('user', '')).strip()
                    password = str(cfg.get('password', ''))
                    exe_path = str(cfg.get('exe_path', '')).strip() or None
                    if not exe_path:
                        return {'ok': False, 'msg': '请填写券商客户端 exe 路径（如 C:\\同花顺\\xiadan.exe）'}
                    trading_api = EasyTraderAPI(broker=broker, exe_path=exe_path)
                    self._log('正在连接券商客户端 (%s)...' % broker)
                    trading_api.connect(user=user, password=password)
                    self._log('券商客户端连接成功')
                else:
                    capital = _f(cfg.get('capital', 100000), 100000)
                    trading_api = TradingAPIFactory.create_api(mode, initial_balance=capital)

                stocks = cfg.get('stocks')
                if stocks:
                    if hasattr(stocks, 'split'):
                        stocks = [s.strip() for s in stocks.replace('，', ',').split(',') if s.strip()]
                    stocks = [str(s).strip() for s in stocks if str(s).strip()]
                # 使用混合AI策略：常态决策树 + 异动时切AI API
                if HAS_HYBRID_AI:
                    ai_api_key = str(cfg.get('ai_api_key', '')).strip()
                    ai_api_url = str(cfg.get('ai_api_url', 'https://api.openai.com/v1/chat/completions')).strip()
                    ai_model = str(cfg.get('ai_model', 'gpt-4o-mini')).strip()
                    ai_strategy = HybridAIStrategy(
                        stocks=stocks,
                        api_key=ai_api_key if ai_api_key else None,
                        api_url=ai_api_url if ai_api_url else None,
                        model=ai_model if ai_model else None,
                    )
                    self._log('AI混合策略已加载 (API Key=%s)' % ('有' if ai_api_key else '未设置'))
                else:
                    from auto_trading_engine import MockAIStrategy
                    ai_strategy = MockAIStrategy(stocks=stocks)
                    self._log('HybridAIStrategy不可用，降级使用MockAIStrategy')
                engine = AutoTradingEngine(trading_api, ai_strategy,
                                           allow_off_hours=(mode != 'easytrader'))
                if stocks:
                    self._log('交易股票池已导入 %d 只自选股' % len(stocks))
                engine.set_risk_config(
                    max_single_position_ratio=_f(cfg.get('max_single', 0.2), 0.2),
                    max_total_position_ratio=_f(cfg.get('max_total', 0.9), 0.9),
                    stop_loss_pct=_f(cfg.get('stop_loss', 5.0), 5.0),
                    take_profit_pct=_f(cfg.get('take_profit', 10.0), 10.0),
                    max_daily_trades=int(_f(cfg.get('max_daily_trades', 999999), 999999)),
                )
                # 动态选股调仓：资金先行，实时盘面打分 → 动态目标组合（不预先锁死买哪只）
                if _is_true(cfg.get('picker_enabled')):
                    pool = stocks
                    if not pool:
                        pool = [i['code'] for i in self._watch_handle().all()]
                        if not pool:
                            return {'ok': False, 'msg': '动态选股需要候选股票池：请填入股票池，或先添加自选股'}
                    engine.set_dynamic_picker(
                        capital=_f(cfg.get('preset_capital', 0), _f(cfg.get('capital', 100000), 100000)),
                        pool=pool,
                        scorer=str(cfg.get('picker_scorer', 'momentum') or 'momentum'),
                        target_total_ratio=_f(cfg.get('rebalance_total_ratio', 0.9), 0.9),
                        per_stock_cap_ratio=_f(cfg.get('picker_per_cap', 0.3), 0.3),
                        min_score=_f(cfg.get('picker_min_score', 0.0), 0.0),
                        top_k=int(_f(cfg.get('picker_top_k', 0), 0)),
                        rebalance_band_pct=_f(cfg.get('rebalance_band_pct', 0.05), 0.05),
                        direction=str(cfg.get('rebalance_direction', 'both') or 'both'),
                        handle_out_of_pool=str(cfg.get('rebalance_out_of_pool', 'keep') or 'keep'),
                        min_trade_amount=_f(cfg.get('rebalance_min_amount', 200.0), 200.0),
                        dry_run=_is_true(cfg.get('rebalance_dry_run')),
                        rebalance_interval_sec=int(_f(cfg.get('rebalance_interval', 300), 300)),
                    )
                # 资金驱动调仓（固定池）：预设金额 → 自动建仓 + 定时再平衡
                elif _is_true(cfg.get('preset_capital_enabled')):
                    engine.set_preset_capital(
                        capital=_f(cfg.get('preset_capital', 0), _f(cfg.get('capital', 100000), 100000)),
                        stock_pool=stocks or None,
                        strategy=str(cfg.get('preset_strategy', 'equal') or 'equal'),
                        weights=(cfg.get('preset_weights') or None),
                        rebalance_band_pct=_f(cfg.get('rebalance_band_pct', 0.05), 0.05),
                        direction=str(cfg.get('rebalance_direction', 'both') or 'both'),
                        handle_out_of_pool=str(cfg.get('rebalance_out_of_pool', 'keep') or 'keep'),
                        min_trade_amount=_f(cfg.get('rebalance_min_amount', 200.0), 200.0),
                        dry_run=_is_true(cfg.get('rebalance_dry_run')),
                        target_total_ratio=_f(cfg.get('rebalance_total_ratio', 0.9), 0.9),
                        rebalance_interval_sec=int(_f(cfg.get('rebalance_interval', 0), 0)),
                    )
                engine.start()
                self.engine = engine
                self.trading_api = trading_api
                self._snap_stop.set()
                self._snap_stop.clear()
                threading.Thread(target=self._snapshot_loop, args=(trading_api,), daemon=True).start()
                self._log('全自动交易引擎已启动 (模式: %s)' % mode)
                _save_engine_state({
                    'auto_restart': True,
                    'mode': mode,
                    'started_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'cfg': {k: v for k, v in (cfg or {}).items() if k != 'password'},
                })
                return {'ok': True, 'msg': '引擎已启动'}
            except Exception as e:
                self._log('[ERROR] 启动失败: %s' % e)
                return {'ok': False, 'msg': '启动失败: %s' % e}

    def auto_resume(self) -> dict:
        """服务器启动时若上次引擎未停止（auto_restart=True），自动续跑交易。"""
        state = _load_engine_state()
        if not state.get('auto_restart'):
            return {'ok': False, 'msg': '无需自动续跑'}
        if self.engine is not None:
            return {'ok': False, 'msg': '引擎已在运行'}
        cfg = state.get('cfg') or _load_trading_config()
        self._log('检测到上次交易未停止，正在自动续跑...')
        return self.start(cfg)

    def stop(self) -> dict:
        with self.lock:
            if self.engine is None:
                _save_engine_state({'auto_restart': False})
                return {'ok': True, 'msg': '引擎未运行'}
            try:
                self.engine.stop()
            except Exception as e:
                self._log('[ERROR] 停止异常: %s' % e)
            self.engine = None
            self._snap_stop.set()
            _save_engine_state({'auto_restart': False})
            self._log('引擎已停止')
            return {'ok': True, 'msg': '引擎已停止'}

    def reset_account(self) -> dict:
        """重置模拟账户（清空持仓、恢复初始资金）"""
        with self.lock:
            if self.engine is not None:
                return {'ok': False, 'msg': '请先停止引擎再重置模拟账户'}
            api = getattr(self, 'trading_api', None)
            if api is None:
                from stock_trading_api import TradingAPIFactory
                cfg = _load_trading_config()
                cap = float(cfg.get('capital') or 100000)
                api = TradingAPIFactory.create_api('simulated', initial_balance=cap)
                self.trading_api = api
            try:
                api.reset_account()
                self.logs = []
                return {'ok': True, 'msg': '模拟账户已重置：清空持仓，恢复初始资金'}
            except Exception as e:
                return {'ok': False, 'msg': '重置失败: %s' % e}

    def test_connect(self, cfg) -> dict:
        """不启动引擎，仅检测券商客户端能否连接（实盘引导用）"""
        cfg = cfg or {}
        mode = str(cfg.get('mode', 'simulation'))
        if mode != 'easytrader':
            return {'ok': True, 'msg': '模拟交易无需连接券商客户端'}
        exe_path = str(cfg.get('exe_path', '')).strip()
        if not exe_path:
            exe_path = self._detect_ths_exe()
        if not exe_path:
            return {'ok': False, 'msg': '未找到下单程序(xiadan.exe)，请先「自动检测」或手动填写路径'}
        if not os.path.exists(exe_path):
            return {'ok': False, 'msg': f'路径不存在: {exe_path}，请确认填的是下单程序 xiadan.exe'}
        try:
            from stock_trading_api import EasyTraderAPI
            broker = str(cfg.get('broker', 'universal')).strip() or 'universal'
            api = EasyTraderAPI(broker=broker, exe_path=exe_path)
            api.connect(user=str(cfg.get('user', '')).strip(), password=str(cfg.get('password', '')))
            api.disconnect()
            return {'ok': True, 'msg': f'连接成功（{broker}），下单程序可用', 'exe_path': exe_path}
        except Exception as e:
            return {'ok': False, 'msg': f'连接失败: {e}', 'exe_path': exe_path}

    @staticmethod
    def _detect_ths_exe():
        import glob
        cands = [
            r'C:\同花顺\xiadan.exe',
            r'C:\同花顺\xiadan\xiadan.exe',
        ]
        for c in cands:
            if os.path.exists(c):
                return c
        home = os.path.expanduser('~')
        for pattern in [
            r'C:\*\xiadan.exe',
            r'C:\*\*\xiadan.exe',
            os.path.join(home, 'Downloads', '*', 'xiadan.exe'),
            os.path.join(home, 'Downloads', 'xiadan.exe'),
            os.path.join(home, 'Desktop', '*', 'xiadan.exe'),
        ]:
            hits = glob.glob(pattern)
            if hits:
                return hits[0]
        return ''

    def status(self) -> dict:
        with self.lock:
            running = self.engine is not None
            engine_status = {}
            logs = list(self.logs[-60:])
            if running:
                try:
                    engine_status = self.engine.get_status()
                    if hasattr(engine_status, 'get'):
                        engine_status = {k: str(v) for k, v in engine_status.items()}
                except Exception:
                    engine_status = {}
                # 汇入引擎线程产生的实时日志（扫描/账户快照/交易动作）
                try:
                    for lg in self.engine.trade_logs[-60:]:
                        logs.append('[%s] [%s] %s' % (lg.get('timestamp', ''), lg.get('level', 'INFO'), lg.get('message', '')))
                    logs = logs[-60:]
                except Exception:
                    pass
            return {'running': running, 'engine': engine_status,
                    'logs': logs,
                    'auto_restart': bool(_load_engine_state().get('auto_restart'))}


class WebApi:
    """暴露给前端 JS 的接口。"""

    def __init__(self):
        self.client = SmartDataClient()
        self.long = LongTermAnalyzer(client=self.client)
        self.watch = Watchlist()
        self.trading = TradingController()
        self.portfolio = PortfolioManager()
        self.funds = FundManager()
        self._jobs = {}
        self._job_seq = 0
        self._job_lock = threading.Lock()
        self._sector_cache = {}
        self._sector_em_down = False          # 东财直连被限流后标记，避免反复白等
        self._sector_ak_down = False         # akshare(东财慢通道) 失败后标记
        self._sector_last_err = {}           # kind -> 最近一次错误，供前端提示
        self._monitor = {'running': False, 'codes': [], 'signals': {}, 'log': [], 'interval': 60}
        # 全球证券（港股/美股）预留接口
        try:
            from 全球证券接口预留 import GlobalSecuritiesFacade
            self.global_sec = GlobalSecuritiesFacade(watchlist=self.watch)
        except Exception as _e:
            self.global_sec = None
            print('[WARN] 全球证券预留接口加载失败:', _e)

    # ---------------- 通用 ----------------
    def ping(self):
        return 'pong'

    def ui_init(self):
        try:
            indices = self.market_indices()
        except Exception:
            indices = []
        return {
            'indices': indices,
            'watchlist': self.watch.all(),
            'trading': self.trading.status(),
        }

    def market_indices(self):
        """大盘顶部行情：上证 / 深成 / 沪深300"""
        try:
            targets = ['000001', '399001', '000300']
            df = self.client.get_realtime(targets, use_cache=True)
            names = {'000001': '上证指数', '399001': '深证成指', '000300': '沪深300'}
            want_type = {'000001': 'index', '399001': 'index', '000300': 'index'}
            best = {}
            if df is not None and not df.empty:
                for _, r in df.iterrows():
                    sym = str(r.get('symbol', ''))
                    if sym not in targets:
                        continue
                    rtype = str(r.get('type', ''))
                    cur = best.get(sym)
                    # 优先保留期望类型（指数）的行
                    if cur is None or (rtype == want_type.get(sym) and str(cur.get('type')) != want_type.get(sym)):
                        best[sym] = r
            rows = []
            for sym in targets:
                r = best.get(sym)
                if r is None:
                    continue
                rows.append({'symbol': sym, 'name': names[sym], 'price': _f(r.get('price')),
                             'pct': _f(r.get('change_percent'))})
            return rows
        except Exception:
            return []

    # ---------------- 推荐榜单 ----------------
    def ranking_start(self, kind='both', limit=20):
        try:
            limit = max(5, min(int(limit), 100))
        except (TypeError, ValueError):
            limit = 20
        with self._job_lock:
            self._job_seq += 1
            jid = 'job_%d' % self._job_seq
        state = {'id': jid, 'running': True, 'done': False, 'message': '任务启动中...',
                 'pct': 0, 'error': None, 'short': [], 'long': []}
        self._jobs[jid] = state

        def run():
            try:
                state['message'] = '抓取全市场快照...'
                if kind in ('both', 'short'):
                    short = self.long.screen_shortterm(limit=limit)
                    state['short'] = _row_dicts(short)
                if kind in ('both', 'long'):
                    state['message'] = '长线深度分析准备中...'
                    state['pct'] = 55

                    def progress(nm, done, limit):
                        state['message'] = f'长线分析中 {done}/{limit}: {nm}'
                        state['pct'] = 55 + int(done * 45 / max(limit, 1))

                    long = self.long.screen_longterm(limit=limit, progress_cb=progress)
                    state['long'] = _row_dicts(long)
                state['message'] = '完成'
                state['pct'] = 100
            except Exception as e:
                state['error'] = str(e)
                state['message'] = '失败: %s' % e
            finally:
                state['running'] = False
                state['done'] = True

        threading.Thread(target=run, daemon=True).start()
        return {'id': jid}

    def ranking_progress(self, jid):
        st = self._jobs.get(jid)
        if st is None:
            return {'running': False, 'done': True, 'pct': 0, 'message': ''}
        return {'running': st['running'], 'done': st['done'], 'pct': st['pct'],
                'message': st['message'], 'error': st['error']}

    def ranking_result(self, jid):
        st = self._jobs.get(jid, {})
        return {'short': st.get('short', []), 'long': st.get('long', [])}

    def ranking_budget(self, total, n=10, mode='mix'):
        """按金额推荐（独立功能）：mode=mix 综合 / hot 追高 / dip 抄底。"""
        try:
            df = self.long.screen_budget(float(total or 0), n=int(n or 10), mode=str(mode or 'mix'))
            return {'ok': True, 'total': float(total or 0), 'mode': str(mode or 'mix'), 'rows': _row_dicts(df)}
        except Exception as e:
            return {'ok': False, 'msg': str(e), 'total': float(total or 0), 'rows': []}

    # ---------------- 我的自选 ----------------
    def trading_budget_hint(self, total, prices=None):
        """根据用户预算+候选股票价格，给出友好的购买力提示。

        prices: {code: price} 可选。若不提供则用全市场最低价估算。
        返回 dict：
          - ok: bool
          - total_budget: 用户预算（元）
          - min_lot_cost: 市场最便宜 1 手成本（元）
          - can_buy_est: 估算可买股票只数
          - msg: 友好提示文字
          - suggestion: 'increase' / 'enough' / 'plenty'
        """
        try:
            from capital_rebalancer import budget_hint as _bh
            total = float(total or 0)
            if total <= 0:
                return {'ok': False, 'msg': '请输入有效金额'}
            if prices:
                prices_dict = {str(k): float(v) for k, v in (prices or {}).items() if v}
            else:
                prices_dict = {}
            h = _bh(total, prices_dict if prices_dict else None)
            can = h['can_buy']
            if can == 0:
                sug = 'increase'
            elif can <= 2:
                sug = 'enough'
            else:
                sug = 'plenty'
            return {
                'ok': True,
                'total_budget': total,
                'min_lot_cost': h['min_needed'],
                'can_buy_est': can,
                'msg': h['msg'],
                'suggestion': sug,
            }
        except Exception as exc:
            return {'ok': False, 'msg': str(exc)}


    def watch_list(self):
        return self.watch.all()

    def watch_add(self, code, name):
        code = str(code).strip()
        name = str(name).strip()
        if not code:
            return {'ok': False, 'msg': '请输入股票代码'}
        try:
            syms = self.client.resolve(code)
            if syms and syms[0].type == 'stock' and syms[0].name:
                name = name or syms[0].name
        except Exception:
            pass
        ok, msg = self.watch.add(code, name or code)
        return {'ok': ok, 'msg': msg}

    def watch_del(self, code):
        ok, msg = self.watch.remove(str(code).strip())
        return {'ok': ok, 'msg': msg}

    def watch_clear(self):
        self.watch.remove_all()
        return {'ok': True, 'msg': '已清空自选股'}

    def watch_refresh(self):
        items = self.watch.all()
        codes = [i['code'] for i in items]
        if not codes:
            return {'rows': [], 'msg': '自选股为空'}
        try:
            df = self.client.get_realtime(codes, use_cache=True)
            rows = _row_dicts(df)
            return {'rows': rows, 'msg': 'ok'}
        except Exception as e:
            return {'rows': [], 'msg': '刷新失败: %s' % e}

    # ---------------- 我的持仓 ----------------
    def _pos_row(self, p):
        profit = p.get_profit_loss()
        cost = p.total_cost or 0
        return {
            'code': p.stock_code, 'name': p.stock_name,
            'volume': _f(p.volume), 'avg_price': round(_f(p.avg_price), 3),
            'current_price': round(_f(p.current_price), 3),
            'total_cost': round(_f(p.total_cost), 2),
            'current_value': round(_f(p.current_value), 2),
            'profit': round(profit, 2),
            'profit_pct': round(profit / cost * 100, 2) if cost else 0.0,
            'buy_date': str(getattr(p, 'buy_date', '')),
        }

    def portfolio_get(self):
        pm = self.portfolio
        positions = sorted(pm.get_position_list(), key=lambda x: x.current_value, reverse=True)
        total_value = pm.get_total_value()
        total_profit = pm.get_total_profit_loss()
        return {
            'ok': True,
            'cash': round(pm.cash, 2),
            'initial_cash': round(pm.initial_cash, 2),
            'total_value': round(total_value, 2),
            'total_profit': round(total_profit, 2),
            'total_profit_pct': round(total_profit / (total_value - total_profit) * 100, 2) if (total_value - total_profit) else 0.0,
            'positions': [self._pos_row(p) for p in positions],
            'history': list(reversed(pm.history[-100:])),
        }

    def portfolio_add(self, code, name, volume, price):
        code = str(code).strip()
        if not code or not name:
            name = code
        try:
            volume = float(volume); price = float(price)
        except (TypeError, ValueError):
            return {'ok': False, 'msg': '请输入有效的数量与价格'}
        if volume <= 0 or price <= 0:
            return {'ok': False, 'msg': '数量与价格必须大于0'}
        ok = self.portfolio.add_position(code, str(name).strip(), volume, price)
        return {'ok': ok, 'msg': '买入成功' if ok else '资金不足，买入失败'}

    def portfolio_sell(self, code, volume, price):
        code = str(code).strip()
        try:
            volume = float(volume); price = float(price)
        except (TypeError, ValueError):
            return {'ok': False, 'msg': '请输入有效的数量与价格'}
        if volume <= 0:
            return {'ok': False, 'msg': '数量必须大于0'}
        ok = self.portfolio.reduce_position(code, volume, price)
        return {'ok': ok, 'msg': '卖出成功' if ok else '卖出失败（无此持仓或数量超限）'}

    def portfolio_update(self, code, name, volume, avg_price):
        """直接修改/新增一条持仓（数量<=0 删除）"""
        try:
            volume = float(volume); avg_price = float(avg_price)
        except (TypeError, ValueError):
            return {'ok': False, 'msg': '请输入有效的数量与价格'}
        code = str(code).strip()
        if not code:
            return {'ok': False, 'msg': '请输入股票代码'}
        self.portfolio.update_position(code, str(name or code).strip(), volume, avg_price)
        return {'ok': True, 'msg': '持仓已更新'}

    def portfolio_remove(self, code):
        self.portfolio.remove_position(str(code).strip())
        return {'ok': True, 'msg': '已删除持仓'}

    def portfolio_set_cash(self, amount):
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return {'ok': False, 'msg': '请输入有效的金额'}
        self.portfolio.set_cash(amount)
        return {'ok': True, 'msg': '可用资金已设置为 %.2f' % amount}

    def portfolio_refresh_prices(self):
        """用实时行情刷新所有持仓的最新价"""
        codes = [p.stock_code for p in self.portfolio.get_position_list()]
        if not codes:
            return {'ok': True, 'msg': '暂无持仓'}
        try:
            df = self.client.get_realtime(codes, use_cache=True)
            price_map = {}
            for _, r in df.iterrows():
                sym = str(r.get('symbol', ''))
                price = _f(r.get('price'))
                if sym in codes and price > 0:
                    price_map[sym] = price
            self.portfolio.update_all_prices(price_map)
            return {'ok': True, 'msg': '已刷新 %d 只持仓价格' % len(price_map)}
        except Exception as e:
            return {'ok': False, 'msg': '刷新失败: %s' % e}

    def portfolio_clear(self):
        self.portfolio.clear_portfolio()
        return {'ok': True, 'msg': '持仓已清空'}

    # ---------------- 资金管理 ----------------
    def _fund_records_file(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fund_records.json')

    def _load_fund_records(self):
        try:
            if os.path.exists(self._fund_records_file()):
                with open(self._fund_records_file(), 'r', encoding='utf-8') as f:
                    return json.load(f) or []
        except Exception:
            pass
        return []

    def _save_fund_records(self, records):
        try:
            with open(self._fund_records_file(), 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def fund_records_get(self):
        records = self._load_fund_records()
        net = sum(r['amount'] if r['type'] == '存入' else -r['amount'] for r in records)
        return {
            'records': list(reversed(records)),
            'total_in': round(sum(r['amount'] for r in records if r['type'] == '存入'), 2),
            'total_out': round(sum(r['amount'] for r in records if r['type'] == '取出'), 2),
            'net_in': round(net, 2),
        }

    def fund_record_add(self, rtype, amount, note=''):
        rtype = str(rtype or '').strip()
        if rtype not in ('存入', '取出'):
            return {'ok': False, 'msg': '类型须为存入或取出'}
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return {'ok': False, 'msg': '请输入有效金额'}
        if amount <= 0:
            return {'ok': False, 'msg': '金额必须大于0'}
        records = self._load_fund_records()
        if rtype == '取出' and amount > sum(r['amount'] if r['type'] == '存入' else -r['amount'] for r in records):
            return {'ok': False, 'msg': '余额不足，无法取出'}
        balance = sum(r['amount'] if r['type'] == '存入' else -r['amount'] for r in records)
        records.append({
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'type': rtype,
            'amount': amount,
            'balance': balance + (amount if rtype == '存入' else -amount),
            'note': str(note or '').strip(),
        })
        if not self._save_fund_records(records):
            return {'ok': False, 'msg': '保存失败'}
        if rtype == '存入':
            self.portfolio.cash += amount
        else:
            self.portfolio.cash = max(0, self.portfolio.cash - amount)
        self.portfolio.save_portfolio()
        return {'ok': True, 'msg': '%s %.2f 元成功' % (rtype, amount)}

    def fund_record_del(self, index):
        """删除一条资金记录（index 为前端展示顺序：0=最新一条）"""
        records = self._load_fund_records()
        try:
            index = int(index)
            rec = records[len(records) - 1 - index]
            del records[len(records) - 1 - index]
        except (IndexError, ValueError, TypeError):
            return {'ok': False, 'msg': '记录不存在'}
        self._save_fund_records(records)
        if rec['type'] == '存入':
            self.portfolio.cash = max(0, self.portfolio.cash - rec['amount'])
        else:
            self.portfolio.cash += rec['amount']
        self.portfolio.save_portfolio()
        return {'ok': True, 'msg': '已删除记录并回滚资金'}

    def fund_records_clear(self):
        self._save_fund_records([])
        return {'ok': True, 'msg': '资金记录已清空'}

    # ---------------- 基金交易 ----------------
    def fund_lookup(self, code):
        """查询基金（优先实时行情，回退 akshare 净值）"""
        code = str(code).strip()
        if not code:
            return {'ok': False, 'msg': '请输入基金代码'}
        try:
            df = self.client.get_realtime(code, types_hint=['fund'])
            if df is not None and not df.empty:
                r = df.iloc[0]
                nav = _f(r.get('price')) or _f(r.get('最新价'))
                if nav > 0:
                    return {'ok': True, 'code': code, 'name': str(r.get('name', code)),
                            'fund_type': '基金', 'nav': round(nav, 4), 'nav_date': '实时',
                            'price': round(nav, 4), 'change': _f(r.get('change_percent'))}
        except Exception:
            pass
        try:
            import akshare as ak
            etf = ak.fund_etf_spot_em()
            info = etf[etf['基金代码'] == code]
            if not info.empty:
                row = info.iloc[0]
                return {'ok': True, 'code': code, 'name': str(row.get('基金名称', code)),
                        'fund_type': 'ETF基金', 'nav': round(_f(row.get('最新价')), 4), 'nav_date': '实时',
                        'price': round(_f(row.get('最新价')), 4), 'change': _f(row.get('涨跌幅'))}
            hist = ak.fund_em_open_fund_info(fund=code, indicator="单位净值走势")
            if hist is not None and not hist.empty:
                nav = float(hist.iloc[-1]['单位净值'])
                return {'ok': True, 'code': code, 'name': str(hist.iloc[-1].get('基金简称', code)),
                        'fund_type': '开放式基金', 'nav': round(nav, 4),
                        'nav_date': str(hist.iloc[-1].get('净值日期', '')),
                        'price': round(nav, 4), 'change': 0.0}
        except Exception as e:
            return {'ok': False, 'msg': '基金查询失败: %s' % e}
        return {'ok': False, 'msg': '未找到基金 %s' % code}

    def fund_search(self, keyword):
        keyword = str(keyword or '').strip()
        if not keyword:
            return {'rows': []}
        try:
            import akshare as ak
            etf = ak.fund_etf_spot_em()
            df = etf[etf['基金代码'].astype(str).str.contains(keyword) | etf['基金名称'].astype(str).str.contains(keyword)]
            rows = df.head(30)[['基金代码', '基金名称', '最新价', '涨跌幅']].copy()
            rows.columns = ['code', 'name', 'price', 'change']
            out = []
            for _, r in rows.iterrows():
                out.append({'code': str(r['code']), 'name': str(r['name']),
                            'price': round(_f(r['price']), 4), 'change': _f(r['change'])})
            return {'rows': out}
        except Exception:
            return {'rows': []}

    def fund_portfolio_get(self):
        fm = self.funds
        rows = []
        for f in fm.get_position_list():
            rows.append({
                'code': f.fund_code, 'name': f.fund_name, 'fund_type': f.fund_type,
                'volume': round(_f(f.volume), 2), 'avg_nav': round(_f(f.avg_nav), 4),
                'current_nav': round(_f(f.current_nav), 4),
                'total_cost': round(_f(f.total_cost), 2), 'current_value': round(_f(f.current_value), 2),
                'profit': round(f.get_profit_loss(), 2), 'profit_pct': round(f.get_profit_loss_pct(), 2),
                'buy_date': str(getattr(f, 'buy_date', '')),
            })
        return {'ok': True, 'rows': rows, 'history': list(reversed(fm.history[-100:]))}

    def fund_buy(self, code, name, nav, volume):
        try:
            nav = float(nav); volume = float(volume)
        except (TypeError, ValueError):
            return {'ok': False, 'msg': '请输入有效净值与份额'}
        if nav <= 0 or volume <= 0:
            return {'ok': False, 'msg': '净值与份额必须大于0'}
        code = str(code).strip()
        ok = self.funds.add_position(code, str(name or code).strip(), volume, nav)
        return {'ok': ok, 'msg': '基金买入成功' if ok else '买入失败'}

    def fund_sell(self, code, nav, volume):
        try:
            nav = float(nav); volume = float(volume)
        except (TypeError, ValueError):
            return {'ok': False, 'msg': '请输入有效净值与份额'}
        code = str(code).strip()
        ok = self.funds.reduce_position(code, volume, nav)
        return {'ok': ok, 'msg': '基金卖出成功' if ok else '卖出失败（无此持仓或份额不足）'}

    def fund_refresh_nav(self):
        codes = [f.fund_code for f in self.funds.get_position_list()]
        if not codes:
            return {'ok': True, 'msg': '暂无基金持仓'}
        nav_map = {}
        for code in codes:
            r = self.fund_lookup(code)
            if r.get('ok'):
                nav_map[code] = r['nav']
        self.funds.update_all_nav(nav_map)
        return {'ok': True, 'msg': '已刷新 %d 只基金净值' % len(nav_map)}

    def fund_clear(self):
        self.funds.clear_portfolio()
        return {'ok': True, 'msg': '基金持仓已清空'}

    # ---------------- 热门板块 ----------------
    def _sector_board(self, kind, cache_minutes=10):
        """获取板块排行，带内存缓存。kind: concept/industry

        网络顺序（快速失败 + 多源兜底）：
          1) 东财 push2 clist 直连（当前网络下最快、最稳，0.4s）
          2) akshare 东财慢通道（被限流时快速跳过，不再每次白等 6s）
          3) 新浪行业板块（行业兜底）
        任一步成功后写缓存；全失败则记录 _sector_last_err 供前端提示。"""
        cache = self._sector_cache.get(kind)
        if cache and time.time() - cache[0] < cache_minutes * 60:
            return cache[1]

        df = None
        last_err = ''
        # 1) 东财直连 clist（最快）
        try:
            df = self._em_board_direct(kind)
            if df is not None and not df.empty:
                last_err = ''
        except Exception as e:
            last_err = '东财直连: %s' % e

        # 2) akshare 慢通道（确认坏了就跳过，避免反复白等）
        if (df is None or df.empty) and not self._sector_ak_down:
            try:
                import akshare as ak
                if kind == 'industry':
                    df2 = ak.stock_board_industry_name_em()
                else:
                    df2 = ak.stock_board_concept_name_em()
                if df2 is not None and not df2.empty:
                    df = df2
                    last_err = ''
            except Exception as e:
                self._sector_ak_down = True   # 标坏，之后不再尝试
                last_err = last_err or ('akshare: %s' % e)

        # 3) 新浪行业兜底
        if (df is None or df.empty) and kind == 'industry':
            try:
                df3 = self._sina_industry_board()
                if df3 is not None and not df3.empty:
                    df = df3
                    last_err = ''
            except Exception as e:
                last_err = last_err or ('新浪: %s' % e)

        self._sector_last_err[kind] = last_err
        if df is not None and not df.empty:
            self._sector_cache[kind] = (time.time(), df)
            return df
        # 全源失败：若有旧缓存（哪怕超过 TTL），降级返回旧数据，避免整页空白
        stale = self._sector_cache.get(kind)
        if stale is not None and stale[1] is not None and not (
                hasattr(stale[1], 'empty') and stale[1].empty):
            self._sector_last_err[kind] = (last_err or '') + '（已降级显示上一次缓存）'
            return stale[1]
        return df

    def _em_board_direct(self, kind):
        """东财 push2 clist 直连板块排行（绕开 akshare 慢通道，最快最稳）。
        概念: fs=m:90 t:3 / 行业: fs=m:90 t:2。列名规整为 akshare 同款：
        板块名称/板块代码/最新价/涨跌幅/上涨家数/下跌家数/总市值。"""
        import requests
        import pandas as _pd
        fs = 'm:90 t:3' if kind == 'concept' else 'm:90 t:2'
        hosts = ['https://push2.eastmoney.com',
                 'https://push2delay.eastmoney.com',
                 'https://push2.eastmoney.com']
        last_exc = None
        r = None
        for host in hosts:
            for _attempt in range(2):
                url = (host + '/api/qt/clist/get?pn=1&pz=200&po=1&np=1'
                       '&fltt=2&invt=2&fid=f3&fs=' + fs +
                       '&fields=f12,f14,f2,f3,f104,f105,f20')
                try:
                    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0',
                                                    'Referer': 'https://quote.eastmoney.com/'},
                                     timeout=6)
                    r.raise_for_status()
                    break
                except Exception as e:
                    last_exc = e
                    time.sleep(0.2)
            if r is not None and r.status_code == 200:
                break
        if r is None:
            raise last_exc or Exception('东财直连无可用 host')
        data = r.json().get('data') or {}
        diff = data.get('diff') or []
        # diff 可能是 list 或 dict（按序号）
        if isinstance(diff, dict):
            diff = list(diff.values())
        if not diff:
            return None
        rows = []
        for x in diff:
            # 只保留 板块（代码 BK 开头）；行业通道的 diff 里会混入个股
            code = str(x.get('f12', ''))
            if not code.startswith('BK'):
                continue
            rows.append({
                '板块名称': x.get('f14', ''),
                '板块代码': code,
                '最新价': _f(x.get('f2')),
                '涨跌幅': _f(x.get('f3')),
                '上涨家数': _f(x.get('f104')),
                '下跌家数': _f(x.get('f105')),
                '总市值': _f(x.get('f20')),
            })
        if not rows:
            return None
        return _pd.DataFrame(rows)

    def _sina_industry_board(self):
        """新浪行业板块（无东财时兜底）"""
        import requests
        try:
            r = requests.get('https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php',
                             headers={'Referer': 'https://finance.sina.com.cn'}, timeout=10)
            text = r.text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start < 0 or end <= start:
                return None
            import json as _json
            data = _json.loads(text[start:end])
            rows = []
            for code, raw in data.items():
                parts = str(raw).split(',')
                if len(parts) < 6:
                    continue
                try:
                    pct = float(parts[5])
                except ValueError:
                    continue
                rows.append({
                    '板块名称': parts[1], '板块代码': code,
                    '最新价': 0.0, '涨跌幅': round(pct, 2),
                    '上涨家数': 0, '下跌家数': 0,
                    '_leader': parts[11] if len(parts) > 11 else '',
                })
            import pandas as pd
            return pd.DataFrame(rows) if rows else None
        except Exception:
            return None

    def sector_hot(self, kind='concept', limit=20):
        try:
            limit = max(5, min(int(limit), 100))
        except (TypeError, ValueError):
            limit = 20
        try:
            df = self._sector_board(kind)
            if df is None or df.empty:
                err = getattr(self, '_sector_last_err', {}).get(kind, '')
                hint = ''
                if kind == 'concept':
                    hint = '；概念板块数据源受限，可切换到「行业板块」或稍后重试'
                return {'rows': [],
                        'msg': '板块接口暂时不可用（%s），请稍后重试%s' % (err or '网络限制', hint)}
            rows = []
            for _, r in df.head(limit).iterrows():
                rows.append({
                    'name': str(r.get('板块名称', '')),
                    'code': str(r.get('板块代码', '')),
                    'price': round(_f(r.get('最新价')), 2),
                    'change_pct': round(_f(r.get('涨跌幅')), 2),
                    'total_mv': round(_f(r.get('总市值')), 0),
                    'up': _f(r.get('上涨家数')),
                    'down': _f(r.get('下跌家数')),
                })
            return {'rows': rows}
        except Exception as e:
            return {'rows': [], 'msg': str(e)}

    def sector_constituents(self, kind, name):
        """板块成分股（含实时行情）。

        多源：优先 akshare 东财（含换手率），失败则走 东财 push2 clist 直连
        （先查板块代码 BK，再拉成分股），保证网络限制下仍能用。"""
        rows = self._sector_cons_akshare(kind, name)
        if not rows:
            rows = self._sector_cons_direct(kind, name)
        return {'rows': rows, 'name': str(name)}

    def _sector_cons_akshare(self, kind, name):
        try:
            import akshare as ak
            if kind == 'industry':
                df = ak.stock_board_industry_cons_em(symbol=str(name))
            else:
                df = ak.stock_board_concept_cons_em(symbol=str(name))
            if df is None or df.empty:
                return []
            out = []
            for _, r in df.iterrows():
                out.append({
                    'code': str(r.get('代码', '')),
                    'name': str(r.get('名称', '')),
                    'price': round(_f(r.get('最新价')), 2),
                    'change_pct': round(_f(r.get('涨跌幅')), 2),
                    'volume': _f(r.get('成交量')),
                    'amount': round(_f(r.get('成交额')), 0),
                    'turnover': round(_f(r.get('换手率')), 2),
                })
            return out
        except Exception:
            return []

    def _sector_board_code(self, kind, name):
        """按名称找板块 BK 代码（从东财直连排行里匹配）。"""
        try:
            df = self._em_board_direct(kind)
            if df is None or df.empty:
                return ''
            hit = df[df['板块名称'].astype(str).str.contains(str(name), na=False, regex=False)]
            if not hit.empty:
                return str(hit.iloc[0]['板块代码'])
        except Exception:
            pass
        return ''

    def _sector_cons_direct(self, kind, name):
        """东财 push2 clist 直连 板块成分股（fs=b:BKxxxx），多 host + 重试。"""
        import requests
        bk = self._sector_board_code(kind, name)
        if not bk:
            return []
        hosts = ['https://push2.eastmoney.com', 'https://push2delay.eastmoney.com']
        data = {}
        for host in hosts:
            url = (host + '/api/qt/clist/get?pn=1&pz=300&po=1&np=1'
                   '&fltt=2&invt=2&fid=f3&fs=b:' + bk +
                   '&fields=f12,f14,f2,f3,f5,f6,f8')
            for _attempt in range(2):
                try:
                    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0',
                                                    'Referer': 'https://quote.eastmoney.com/'},
                                     timeout=6)
                    r.raise_for_status()
                    data = r.json().get('data') or {}
                    if data:
                        break
                except Exception:
                    time.sleep(0.2)
            if data:
                break
        diff = data.get('diff') or []
        if isinstance(diff, dict):
            diff = list(diff.values())
        out = []
        for x in diff:
            out.append({
                'code': str(x.get('f12', '')),
                'name': str(x.get('f14', '')),
                'price': round(_f(x.get('f2')), 2),
                'change_pct': round(_f(x.get('f3')), 2),
                'volume': _f(x.get('f5')),
                'amount': round(_f(x.get('f6')), 0),
                'turnover': round(_f(x.get('f8')), 2),
            })
        return out

    def sector_search(self, kind, keyword):
        """按关键词搜索板块"""
        keyword = str(keyword or '').strip()
        try:
            df = self._sector_board(kind)
            if df is None or df.empty:
                return {'rows': []}
            hit = df[df['板块名称'].astype(str).str.contains(keyword, na=False)]
            rows = [{'name': str(r['板块名称']), 'code': str(r['板块代码']),
                     'price': round(_f(r.get('最新价')), 2), 'change_pct': round(_f(r.get('涨跌幅')), 2)}
                    for _, r in hit.head(20).iterrows()]
            return {'rows': rows}
        except Exception as e:
            return {'rows': [], 'msg': str(e)}

    # ---------------- 实时行情 ----------------
    def rt_overview(self):
        """市场概览：从全市场快照统计涨跌家数/涨停跌停/总成交额"""
        try:
            snap = self.long.get_market_snapshot(use_cache=True)
            if snap is None or snap.empty:
                return {'ok': False, 'msg': '快照获取失败'}
            snap['涨跌幅'] = pd.to_numeric(snap['涨跌幅'], errors='coerce')
            snap['成交额'] = pd.to_numeric(snap['成交额'], errors='coerce')
            pct = snap['涨跌幅'].fillna(0)
            return {
                'ok': True,
                'update_time': time.strftime('%H:%M:%S'),
                'total': int(len(snap)),
                'up': int((pct > 0).sum()),
                'down': int((pct < 0).sum()),
                'flat': int((pct == 0).sum()),
                'limit_up': int((pct >= 9.9).sum()),
                'limit_down': int((pct <= -9.9).sum()),
                'turnover_yi': round(float(snap['成交额'].fillna(0).sum()) / 1e8, 0),
            }
        except Exception as e:
            return {'ok': False, 'msg': str(e)}

    def rt_quotes(self, text, types_hint='stock'):
        """批量实时行情（轻量，不含深度分析）"""
        try:
            types = [types_hint] if types_hint in ('stock', 'index', 'fund') else None
            df = self.client.get_realtime(text, types_hint=types, use_cache=True)
            return {'ok': True, 'rows': _row_dicts(df)}
        except Exception as e:
            return {'ok': False, 'rows': [], 'msg': str(e)}

    def rt_indices(self):
        """主要大盘指数实时行情"""
        targets = ['000001', '399001', '399006', '000688', '000300', '000016', '000905']
        names = {'000001': '上证指数', '399001': '深证成指', '399006': '创业板指',
                 '000688': '科创50', '000300': '沪深300', '000016': '上证50', '000905': '中证500'}
        try:
            df = self.client.get_realtime(targets, types_hint=['index'], use_cache=True)
            rows = []
            if df is not None and not df.empty:
                for _, r in df.iterrows():
                    sym = str(r.get('symbol', ''))
                    if sym in names:
                        rows.append({'symbol': sym, 'name': names[sym],
                                     'price': round(_f(r.get('price')), 2),
                                     'pct': round(_f(r.get('change_percent')), 2)})
            return {'rows': rows}
        except Exception:
            return {'rows': []}

    # ---------------- 数据抓取 ----------------
    def crawl_history(self, codes, start='', end=''):
        """批量下载历史K线并存 CSV。codes: 逗号分隔。返回任务 job_id"""
        import re as _re
        if isinstance(codes, str):
            codes = [c.strip() for c in _re.split(r'[，,;\s]+', codes) if c.strip()]
        if not codes:
            return {'ok': False, 'msg': '请输入股票代码'}
        s = str(start or '').strip().replace('-', '').replace('/', '')
        e = str(end or '').strip().replace('-', '').replace('/', '')
        if s and (len(s) != 8 or not s.isdigit()):
            s = ''
        if e and (len(e) != 8 or not e.isdigit()):
            e = ''
        with self._job_lock:
            self._job_seq += 1
            jid = 'job_%d' % self._job_seq
        state = {'id': jid, 'running': True, 'done': False, 'pct': 0,
                 'message': '启动中...', 'error': None, 'results': []}
        self._jobs[jid] = state

        def run():
            from 增强版数据爬取 import EnhancedDataCrawler, DATA_DIR as CR_DATADIR
            crawler = EnhancedDataCrawler(use_all_sources=True)
            total = len(codes)
            done = 0
            for code in codes:
                path = None
                try:
                    df = crawler.get_stock_daily(code, s or None, e or None)
                    if df is not None and not df.empty:
                        if s or e:
                            dcol = '日期' if '日期' in df.columns else df.columns[0]
                            dser = df[dcol].astype(str).str.replace('-', '', regex=False).str.replace('/', '', regex=False)
                            if s:
                                df = df[dser >= s]
                                dser = dser[dser >= s]
                            if e:
                                df = df[dser <= e]
                        if df is not None and not df.empty:
                            fn = os.path.join(CR_DATADIR, '%s_daily.csv' % code)
                            df.to_csv(fn, index=False, encoding='utf-8-sig')
                            path = '%s_daily.csv' % code
                            state['results'].append({'code': code, 'ok': True, 'rows': len(df), 'file': path})
                        else:
                            state['results'].append({'code': code, 'ok': False, 'msg': '日期范围内无数据'})
                    else:
                        state['results'].append({'code': code, 'ok': False, 'msg': '无数据'})
                except Exception as exc:
                    state['results'].append({'code': code, 'ok': False, 'msg': str(exc)[:80]})
                done += 1
                state['pct'] = int(done * 100 / max(total, 1))
                state['message'] = '下载中 %d/%d: %s' % (done, total, code)
            state['message'] = '完成'
            state['pct'] = 100
            state['running'] = False
            state['done'] = True
        threading.Thread(target=run, daemon=True).start()
        return {'ok': True, 'id': jid}

    def crawl_progress(self, jid):
        st = self._jobs.get(jid)
        if st is None:
            return {'running': False, 'done': True, 'pct': 0, 'message': '', 'results': []}
        return {'running': st['running'], 'done': st['done'], 'pct': st['pct'],
                'message': st['message'], 'error': st['error'], 'results': st.get('results', [])}

    def crawl_list(self):
        """数据目录文件列表"""
        import glob as _glob
        try:
            from 爬取金融数据 import DATA_DIR
        except Exception:
            DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'financial_data')
        files = []
        if os.path.isdir(DATA_DIR):
            for f in sorted(_glob.glob(os.path.join(DATA_DIR, '*.csv'))):
                files.append({'name': os.path.basename(f), 'size_kb': round(os.path.getsize(f) / 1024, 1)})
        return {'dir': DATA_DIR, 'files': files}

    def crawl_delete(self, filename):
        try:
            from 爬取金融数据 import DATA_DIR
        except Exception:
            DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'financial_data')
        path = os.path.join(DATA_DIR, os.path.basename(str(filename)))
        if os.path.exists(path) and path.endswith('.csv'):
            os.remove(path)
            return {'ok': True, 'msg': '已删除 %s' % os.path.basename(path)}
        return {'ok': False, 'msg': '文件不存在'}

    # ---------------- 回测 ----------------
    def backtest_models(self):
        try:
            from 多模型AI量化交易 import AI_MODELS
            return [{'id': k, 'name': v['name'], 'desc': v['description'],
                     'speed': v['speed'], 'accuracy': v['accuracy']} for k, v in AI_MODELS.items()]
        except Exception as e:
            return []

    def backtest_start(self, code, start, end, model='1', capital=None):
        try:
            initial_cash = max(100.0, float(capital or 0) or 500000.0)
        except Exception:
            initial_cash = 500000.0
        codes = [c.strip().zfill(6) for c in str(code or '').replace('\n', ',').replace('，', ',').replace(' ', '').split(',') if c.strip()]
        codes = list(dict.fromkeys(codes))
        if not codes:
            return {'ok': False, 'msg': '请输入股票代码'}
        s = str(start or '').replace('-', '').replace('/', '')
        e = str(end or '').replace('-', '').replace('/', '')
        with self._job_lock:
            self._job_seq += 1
            jid = 'job_%d' % self._job_seq
        state = {'id': jid, 'running': True, 'done': False, 'pct': 0,
                 'message': '回测启动中...', 'error': None, 'result': None}
        self._jobs[jid] = state

        def run():
            for _s in (sys.stdout, sys.stderr):
                try:
                    _s.reconfigure(encoding='utf-8', errors='replace')
                except Exception:
                    pass
            try:
                from 多模型AI量化交易 import MultiModelBacktester
                from 增强版数据爬取 import EnhancedDataCrawler
                import datetime as _dt
                state['message'] = '下载历史数据（%d 只）...' % len(codes)
                def _d8(x):
                    return str(x or '').replace('-', '').replace('/', '')
                s8 = _d8(s)
                e8 = _d8(e) or time.strftime('%Y%m%d')
                # AI训练至少需约120行，区间过短时自动向前扩展
                try:
                    sd = _dt.datetime.strptime(s8, '%Y%m%d') if s8 else None
                    ed = _dt.datetime.strptime(e8, '%Y%m%d')
                    if sd is None or (ed - sd).days < 400:
                        s8 = ((sd or ed) - _dt.timedelta(days=730)).strftime('%Y%m%d')
                except Exception:
                    s8 = (ed - _dt.timedelta(days=730)).strftime('%Y%m%d')
                crawler = EnhancedDataCrawler(use_all_sources=True)
                data_map = {}
                dcol = '日期'
                for c in codes:
                    try:
                        # 优先腾讯直连 fqkline（最稳定），失败再走增强爬取
                        df = None
                        try:
                            df = self.long.fetch_history(c, years=3)
                        except Exception:
                            df = None
                        if df is None or df.empty:
                            df = crawler.get_stock_daily(c, s8, e8)
                        if df is None or df.empty:
                            continue
                        dcol = '日期' if '日期' in df.columns else df.columns[0]
                        dser = df[dcol].astype(str).str.replace('-', '', regex=False)
                        df = df[(dser >= s8) & (dser <= e8)]
                        if df is not None and not df.empty and len(df) >= 120:
                            data_map[c] = df
                        else:
                            state['message'] += '  %s数据不足120条，跳过' % c
                    except Exception:
                        continue
                if not data_map:
                    state['error'] = '数据获取失败或不足120条（请扩大日期范围）'
                    state['message'] = '失败：无有效数据'
                    return
                state['message'] = '运行组合回测（%d 只，初始资金 %s 元，AI模型训练中，可能较慢）...' % (
                    len(data_map), format(initial_cash, ',.0f'))
                bt = MultiModelBacktester(model_type=str(model), use_ai=True, initial_cash=initial_cash)
                res = bt.run_combined_backtest(data_map)
                if res is None:
                    state['error'] = '回测失败（数据或模型问题）'
                    state['message'] = '回测失败'
                else:
                    state['result'] = {k: (float(res[k]) if hasattr(res[k], 'item') else res[k])
                                       for k in ('model_name', 'returns', 'win_rate', 'total_trades',
                                                 'buy_hold_return', 'final_value', 'initial_cash')}
                    state['result']['stock_count'] = res.get('stock_count', len(data_map))
                    state['result']['per_stock'] = res.get('per_stock', [])
                    state['result']['capital_skipped'] = res.get('capital_skipped', [])
                    # 绩效指标（借鉴主流量化框架：Sharpe/回撤/Calmar/成本感知）
                    state['result']['perf'] = res.get('perf', {})
                    state['result']['total_cost'] = res.get('total_cost', 0.0)
                    state['result']['total_turnover'] = res.get('total_turnover', 0.0)
                    state['result']['commission_rate'] = res.get('commission_rate', 0.0)
                    state['result']['slippage_rate'] = res.get('slippage_rate', 0.0)
                    state['result']['walk_forward_folds'] = res.get('walk_forward_folds', 0)
                    state['message'] = '完成'
            except Exception as exc:
                state['error'] = str(exc)[:120]
                state['message'] = '失败'
            finally:
                state['running'] = False
                state['done'] = True
                state['pct'] = 100
        threading.Thread(target=run, daemon=True).start()
        return {'ok': True, 'id': jid}

    def backtest_progress(self, jid):
        st = self._jobs.get(jid)
        if st is None:
            return {'running': False, 'done': True, 'pct': 0, 'message': '', 'result': None, 'error': ''}
        return {'running': st['running'], 'done': st['done'], 'pct': st['pct'],
                'message': st['message'], 'result': st.get('result'), 'error': st.get('error')}

    # ---------------- 盘中监控 ----------------
    def _monitor_log(self, msg, level='INFO'):
        self._monitor['log'].append(time.strftime('%H:%M:%S') + ' [' + level + '] ' + msg)
        if len(self._monitor['log']) > 200:
            self._monitor['log'] = self._monitor['log'][-200:]

    def monitor_start(self, codes, model='1', interval=60):
        import re as _re
        if isinstance(codes, str):
            codes = [c.strip() for c in _re.split(r'[，,;\s]+', codes) if c.strip()]
        if not codes:
            return {'ok': False, 'msg': '请输入股票代码'}
        if self._monitor['running']:
            return {'ok': False, 'msg': '监控已在运行，请先停止'}
        try:
            interval = max(15, min(int(interval), 3600))
        except (TypeError, ValueError):
            interval = 60
        self._monitor['running'] = True
        self._monitor['codes'] = codes
        self._monitor['interval'] = interval
        self._monitor['signals'] = {}
        self._monitor['log'] = []
        self._monitor_log('盘中监控启动：%d 只股票，模型 %s，间隔 %d 秒' % (len(codes), model, interval))

        def run():
            for _s in (sys.stdout, sys.stderr):
                try:
                    _s.reconfigure(encoding='utf-8', errors='replace')
                except Exception:
                    pass
            try:
                from 多模型AI量化交易 import RealTimeMonitor
                rt = RealTimeMonitor(codes, model_type=str(model), refresh_interval=interval)
                while self._monitor['running']:
                    for code in codes:
                        try:
                            sig = rt.get_realtime_signal(code)
                            if sig:
                                self._monitor['signals'][code] = {
                                    'code': code, 'date': sig['date'], 'price': round(_f(sig['price']), 2),
                                    'change_pct': round(_f(sig['change_pct']), 2),
                                    'buy': bool(sig['buy_signal']), 'sell': bool(sig['sell_signal']),
                                    'ai': int(sig.get('ai_signal') or 0),
                                    'rsi': round(_f(sig.get('rsi')), 2) if sig.get('rsi') is not None else None,
                                    'macd': round(_f(sig.get('macd')), 3) if sig.get('macd') is not None else None,
                                }
                        except Exception as e:
                            self._monitor_log('%s 信号获取失败: %s' % (code, str(e)[:60]), 'ERROR')
                    self._monitor_log('第 %d 轮信号扫描完成' % int(self._monitor.get('_cycle', 0) + 1))
                    self._monitor['_cycle'] = int(self._monitor.get('_cycle', 0)) + 1
                    for i in range(interval):
                        if not self._monitor['running']:
                            break
                        time.sleep(1)
            except Exception as e:
                self._monitor_log('监控线程异常: %s' % e, 'ERROR')
            finally:
                self._monitor['running'] = False
        threading.Thread(target=run, daemon=True).start()
        return {'ok': True, 'msg': '监控已启动'}

    def monitor_status(self):
        sigs = []
        for code, s in self._monitor['signals'].items():
            act = '🟢 买入' if s['buy'] else ('🔴 卖出' if s['sell'] else '⚪ 观望')
            ai = {1: '看涨', -1: '看跌'}.get(s['ai'], '中性')
            sigs.append({'code': s['code'], 'price': s['price'], 'change_pct': s['change_pct'],
                         'rsi': s['rsi'], 'macd': s['macd'], 'ai': ai, 'action': act,
                         'date': s['date'], 'buy': s['buy'], 'sell': s['sell']})
        return {'running': self._monitor['running'], 'codes': self._monitor['codes'],
                'interval': self._monitor['interval'], 'signals': sigs,
                'log': list(self._monitor['log'][-60:])}

    def monitor_stop(self):
        self._monitor['running'] = False
        self._monitor_log('监控已停止')
        return {'ok': True, 'msg': '监控已停止'}

    # ---------------- 数据管理 ----------------
    def storage_get(self):
        """统计存储占用：模型文件/股票数据/分析报告"""
        import glob as _glob
        base = os.path.dirname(os.path.abspath(__file__))
        try:
            from 爬取金融数据 import DATA_DIR
        except Exception:
            DATA_DIR = os.path.join(base, 'financial_data')
        analysis_dir = os.path.join(os.path.dirname(DATA_DIR), '分析数据')
        cats = [('模型文件(*.pkl)', 'model', base, '*.pkl'),
                ('股票数据', 'data', DATA_DIR, '*'),
                ('分析报告', 'analysis', analysis_dir, '*')]
        out = []
        total = 0
        for label, ctype, folder, pat in cats:
            files = []
            if os.path.isdir(folder):
                for fp in _glob.glob(os.path.join(folder, pat)):
                    try:
                        if os.path.isfile(fp):
                            sz = os.path.getsize(fp)
                            total += sz
                            files.append({'name': os.path.basename(fp), 'path': fp,
                                          'size_kb': round(sz / 1024, 1), 'type': ctype,
                                          'mtime': time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(fp)))})
                    except Exception:
                        pass
            files.sort(key=lambda x: x['size_kb'], reverse=True)
            out.append({'label': label, 'type': ctype, 'folder': folder,
                        'count': len(files), 'size_mb': round(sum(f['size_kb'] for f in files) / 1024, 1),
                        'files': files[:200]})
        return {'cats': out, 'total_mb': round(total / 1024 / 1024, 1)}

    def storage_delete(self, path):
        path = str(path or '')
        base = os.path.dirname(os.path.abspath(__file__))
        try:
            from 爬取金融数据 import DATA_DIR
        except Exception:
            DATA_DIR = os.path.join(base, 'financial_data')
        analysis_dir = os.path.join(os.path.dirname(DATA_DIR), '分析数据')
        allowed = (os.path.normcase(DATA_DIR), os.path.normcase(analysis_dir), os.path.normcase(base))
        if not any(os.path.normcase(path).startswith(a) for a in allowed):
            return {'ok': False, 'msg': '路径不在可管理范围'}
        if os.path.isfile(path) and (path.endswith('.csv') or path.endswith('.pkl') or path.endswith('.html')):
            os.remove(path)
            return {'ok': True, 'msg': '已删除 %s' % os.path.basename(path)}
        return {'ok': False, 'msg': '仅支持删除 csv/pkl/html 文件'}

    def storage_open_folder(self, which='data'):
        try:
            import subprocess
            base = os.path.dirname(os.path.abspath(__file__))
            try:
                from 爬取金融数据 import DATA_DIR
            except Exception:
                DATA_DIR = os.path.join(base, 'financial_data')
            folder = DATA_DIR if which == 'data' else os.path.join(os.path.dirname(DATA_DIR), '分析数据')
            if os.path.isdir(folder):
                subprocess.Popen(['explorer', folder])
                return {'ok': True, 'msg': '已打开文件夹'}
            return {'ok': False, 'msg': '文件夹不存在'}
        except Exception as e:
            return {'ok': False, 'msg': str(e)}

    # ---------------- 走势分析 ----------------
    def analysis_start(self):
        """对数据目录所有 CSV 批量分析并生成 HTML 报告（异步任务）"""
        with self._job_lock:
            self._job_seq += 1
            jid = 'job_%d' % self._job_seq
        state = {'id': jid, 'running': True, 'done': False, 'pct': 0,
                 'message': '分析启动中...', 'error': None, 'report': None}
        self._jobs[jid] = state

        def run():
            try:
                import sys as _sys
                try:
                    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
                except Exception:
                    pass
                from 分析数据 import FinancialDataAnalyzer
                base = os.path.dirname(os.path.abspath(__file__))
                try:
                    from 爬取金融数据 import DATA_DIR
                except Exception:
                    DATA_DIR = os.path.join(base, 'financial_data')
                out_dir = os.path.join(os.path.dirname(DATA_DIR), '分析数据')
                os.makedirs(out_dir, exist_ok=True)
                ana = FinancialDataAnalyzer(DATA_DIR, out_dir, enable_ai=False)
                files = ana.scan_data_files()
                state['message'] = '找到 %d 个数据文件，开始分析...' % len(files)
                ana.analyze_all_files()
                state['message'] = '生成 HTML 报告...'
                state['pct'] = 80
                report = ana.create_html_report()
                state['pct'] = 100
                state['report'] = report
                state['message'] = '完成'
            except Exception as exc:
                state['error'] = str(exc)[:120]
                state['message'] = '失败'
            finally:
                state['running'] = False
                state['done'] = True
        threading.Thread(target=run, daemon=True).start()
        return {'ok': True, 'id': jid}

    def analysis_progress(self, jid):
        st = self._jobs.get(jid)
        if st is None:
            return {'running': False, 'done': True, 'pct': 0, 'message': '', 'error': '', 'report': None}
        return {'running': st['running'], 'done': st['done'], 'pct': st['pct'],
                'message': st['message'], 'error': st.get('error'), 'report': st.get('report')}

    def analysis_open_report(self):
        try:
            import subprocess
            import glob as _glob
            base = os.path.dirname(os.path.abspath(__file__))
            try:
                from 爬取金融数据 import DATA_DIR
            except Exception:
                DATA_DIR = os.path.join(base, 'financial_data')
            folder = os.path.join(os.path.dirname(DATA_DIR), '分析数据')
            rep = os.path.join(folder, '分析报告.html')
            if not os.path.exists(rep):
                hits = _glob.glob(os.path.join(folder, '*.html'))
                rep = hits[0] if hits else rep
            if os.path.exists(rep):
                subprocess.Popen(['explorer', rep])
                return {'ok': True, 'msg': '已打开报告'}
            return {'ok': False, 'msg': '报告不存在，请先运行分析'}
        except Exception as e:
            return {'ok': False, 'msg': str(e)}

    # ---------------- 数据库管理 ----------------
    def db_status(self):
        """测试数据库连接，返回版本/表/记录数"""
        try:
            from database_config import DB_CONFIG
            from database_manager import DatabaseManager
            db = DatabaseManager()
            if not db.connection:
                return {'ok': False, 'msg': '无法连接数据库，请检查 MySQL 是否启动及 database_config.py 配置'}
            db.cursor.execute('SELECT VERSION()')
            ver = list(db.cursor.fetchone().values())[0]
            db.cursor.execute('SHOW TABLES')
            tables = [list(r.values())[0] for r in db.cursor.fetchall()]
            info = []
            for t in tables:
                try:
                    db.cursor.execute('SELECT COUNT(*) AS c FROM `%s`' % t)
                    cnt = list(db.cursor.fetchone().values())[0]
                except Exception:
                    cnt = 0
                info.append({'table': t, 'rows': cnt})
            db.close()
            return {'ok': True, 'host': DB_CONFIG['host'], 'port': DB_CONFIG['port'],
                    'database': DB_CONFIG['database'], 'version': ver, 'tables': info}
        except Exception as e:
            return {'ok': False, 'msg': str(e)[:150]}

    def db_table_schema(self, table):
        """查看表结构 + 数据预览"""
        try:
            from database_manager import DatabaseManager
            db = DatabaseManager()
            if not db.connection:
                return {'ok': False, 'msg': '无法连接数据库'}
            db.cursor.execute('DESCRIBE `%s`' % table)
            cols = []
            for r in db.cursor.fetchall():
                d = dict(r)
                cols.append({'field': d.get('Field'), 'type': d.get('Type'), 'null': d.get('Null'), 'key': d.get('Key'), 'comment': d.get('Comment', '')})
            db.cursor.execute('SELECT * FROM `%s` LIMIT 50' % table)
            rows = [dict(r) for r in db.cursor.fetchall()]
            db.cursor.execute('SELECT COUNT(*) AS c FROM `%s`' % table)
            total = list(db.cursor.fetchone().values())[0]
            db.close()
            return {'ok': True, 'columns': cols, 'rows': rows, 'total': total}
        except Exception as e:
            return {'ok': False, 'msg': str(e)[:150]}

    def db_sync(self):
        """同步股票基本信息/行情/技术指标到数据库（异步，依赖 akshare，可能超时）"""
        with self._job_lock:
            self._job_seq += 1
            jid = 'job_%d' % self._job_seq
        state = {'id': jid, 'running': True, 'done': False, 'pct': 0,
                 'message': '同步启动中...', 'error': None, 'logs': []}
        self._jobs[jid] = state

        def run():
            import sys as _sys
            try:
                _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
            try:
                from datetime import datetime
                from financial_data_integrator import FinancialDataIntegrator
                integrator = FinancialDataIntegrator()
                state['message'] = '同步股票基本信息（akshare，可能超时）...'
                state['pct'] = 15
                try:
                    integrator.sync_stock_basic_info('沪深A股')
                except Exception as e:
                    state['error'] = '同步股票列表失败: %s' % str(e)[:100]
                    state['logs'].append(state['error'])
                state['message'] = '同步行情数据...'
                state['pct'] = 50
                try:
                    test_codes = ['000001.SZ', '600000.SH']
                    integrator.sync_daily_quotes(test_codes, '2024-01-01', datetime.now().strftime('%Y-%m-%d'))
                except Exception as e:
                    state['logs'].append('同步行情失败: %s' % str(e)[:100])
                state['message'] = '计算技术指标...'
                state['pct'] = 80
                try:
                    integrator.calculate_all_technical_indicators(['000001.SZ', '600000.SH'])
                except Exception as e:
                    state['logs'].append('计算指标失败: %s' % str(e)[:100])
                integrator.close()
                state['pct'] = 100
                if not state['error']:
                    state['message'] = '同步完成'
                else:
                    state['message'] = '完成（部分失败，见日志）'
            except Exception as exc:
                state['error'] = str(exc)[:120]
                state['message'] = '失败'
            finally:
                state['running'] = False
                state['done'] = True
        threading.Thread(target=run, daemon=True).start()
        return {'ok': True, 'id': jid}

    def db_progress(self, jid):
        st = self._jobs.get(jid)
        if st is None:
            return {'running': False, 'done': True, 'pct': 0, 'message': '', 'error': '', 'logs': []}
        return {'running': st['running'], 'done': st['done'], 'pct': st['pct'],
                'message': st['message'], 'error': st.get('error'), 'logs': st.get('logs', [])}

    def db_import_csv(self, filename):
        """将 金融数据 目录下的 CSV 导入数据库（建同名表）"""
        try:
            import pandas as pd
            from database_manager import DatabaseManager
            base = os.path.dirname(os.path.abspath(__file__))
            try:
                from 爬取金融数据 import DATA_DIR
            except Exception:
                DATA_DIR = os.path.join(base, 'financial_data')
            path = os.path.join(DATA_DIR, os.path.basename(str(filename)))
            if not os.path.isfile(path):
                return {'ok': False, 'msg': '文件不存在: %s' % filename}
            df = pd.read_csv(path)
            table = os.path.splitext(os.path.basename(path))[0]
            db = DatabaseManager()
            if not db.connection:
                return {'ok': False, 'msg': '无法连接数据库'}
            cols_sql = ', '.join(['`%s` TEXT' % c.replace('`', '') for c in df.columns])
            db.cursor.execute('CREATE TABLE IF NOT EXISTS `%s` (id INT AUTO_INCREMENT PRIMARY KEY, %s)' % (table, cols_sql))
            placeholders = ', '.join(['%s'] * len(df.columns))
            colnames = ', '.join(['`%s`' % c.replace('`', '') for c in df.columns])
            for _, row in df.iterrows():
                db.cursor.execute('INSERT INTO `%s` (%s) VALUES (%s)' % (table, colnames, placeholders),
                                  tuple('' if pd.isna(v) else str(v) for v in row))
            db.connection.commit()
            db.close()
            return {'ok': True, 'msg': '已导入 %d 行到表 %s' % (len(df), table)}
        except Exception as e:
            return {'ok': False, 'msg': str(e)[:150]}

    def db_export_csv(self, table):
        """导出数据库表为 CSV（保存到 金融数据 目录）"""
        try:
            import pandas as pd
            from database_manager import DatabaseManager
            base = os.path.dirname(os.path.abspath(__file__))
            try:
                from 爬取金融数据 import DATA_DIR
            except Exception:
                DATA_DIR = os.path.join(base, 'financial_data')
            db = DatabaseManager()
            if not db.connection:
                return {'ok': False, 'msg': '无法连接数据库'}
            db.cursor.execute('SELECT * FROM `%s`' % table)
            rows = db.cursor.fetchall()
            db.close()
            if not rows:
                return {'ok': False, 'msg': '表 %s 为空' % table}
            df = pd.DataFrame(rows)
            out = os.path.join(DATA_DIR, 'db_%s.csv' % table)
            df.to_csv(out, index=False, encoding='utf-8-sig')
            return {'ok': True, 'msg': '已导出 %d 行到 %s' % (len(df), os.path.basename(out))}
        except Exception as e:
            return {'ok': False, 'msg': str(e)[:150]}

    # ---------------- 智能查询 ----------------
    def query_stock(self, text):
        text = str(text).strip()
        if not text:
            return {'ok': False, 'msg': '请输入股票名称或代码'}
        out = {'ok': True, 'quotes': [], 'analysis': None}
        try:
            df = self.client.get_realtime(text, use_cache=True)
            out['quotes'] = _row_dicts(df)
        except Exception as e:
            out['ok'] = False
            out['msg'] = '行情查询失败: %s' % e
        try:
            rep = self.long.analyze(text, use_ai=True)
            if 'error' not in rep:
                out['analysis'] = rep
        except Exception:
            pass
        return out

    def query_kline(self, code, days=160):
        """K线数据：最近 N 个交易日 OHLC + 均线(MA5/10/20)"""
        code = str(code).strip()
        if not code:
            return {'ok': False, 'kline': [], 'name': ''}
        try:
            df = self.long.fetch_history(code, years=2)
            if df is None or df.empty:
                return {'ok': False, 'kline': [], 'name': ''}
            df = df.tail(int(days))
            close = df['收盘'].astype(float)
            out = []
            for idx, (_, r) in enumerate(df.iterrows()):
                c = float(r['收盘'])
                m5 = float(close.iloc[max(0, idx - 4):idx + 1].mean())
                m10 = float(close.iloc[max(0, idx - 9):idx + 1].mean())
                m20 = float(close.iloc[max(0, idx - 19):idx + 1].mean())
                out.append({
                    'd': str(r['日期']),
                    'o': round(float(r['开盘']), 2),
                    'h': round(float(r['最高']), 2),
                    'l': round(float(r['最低']), 2),
                    'c': round(c, 2),
                    'v': float(r.get('成交量', 0) or 0),
                    'ma5': round(m5, 2),
                    'ma10': round(m10, 2),
                    'ma20': round(m20, 2),
                })
            name = ''
            try:
                syms = self.client.resolve(code)
                if syms and syms[0].name:
                    name = syms[0].name
            except Exception:
                pass
            return {'ok': True, 'kline': out, 'name': name}
        except Exception as e:
            return {'ok': False, 'kline': [], 'name': '', 'msg': str(e)}

    # ---------------- 自动训练策略 AI（持续学习 + 预测） ----------------
    def _model_path(self):
        import os as _os
        return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'ai_strategy_model.pkl')

    def _samples_path(self):
        import os as _os
        return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'ai_strategy_samples.pkl')

    def _fetch_df(self, code):
        import pandas as pd
        try:
            df = self.client.get_history(code, adjust='qfq')
        except Exception:
            df = None
        if df is None or (hasattr(df, 'empty') and df.empty):
            try:
                from 智能数据查询 import ensure_streams
                ensure_streams()
            except Exception:
                pass
            try:
                import akshare as ak
                df = ak.stock_zh_a_hist(symbol=str(code).zfill(6), period='daily', adjust='qfq')
            except Exception:
                df = None
        if df is None or (hasattr(df, 'empty') and df.empty):
            return None
        rn = {'日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high',
              '最低': 'low', '成交量': 'volume', '成交额': 'amount'}
        df = df.rename(columns=rn)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True).astype(float, errors='ignore')
        return df

    def _build_features(self, df):
        import numpy as np
        c = df['close']
        ma5 = c.rolling(5).mean(); ma10 = c.rolling(10).mean()
        ma20 = c.rolling(20).mean(); ma60 = c.rolling(60).mean()
        df['ret_1'] = c.pct_change(1)
        df['ret_3'] = c.pct_change(3)
        df['ret_5'] = c.pct_change(5)
        df['ret_10'] = c.pct_change(10)
        df['ma_diff'] = (ma5 - ma20) / ma20
        df['ma_diff_60'] = (ma20 - ma60) / ma60
        df['close_above_ma60'] = (c - ma60) / ma60
        delta = c.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = (100 - 100 / (1 + rs)).fillna(50)
        v = df['volume'].astype(float)
        df['vol_chg'] = v.pct_change(5)
        vma20 = v.rolling(20).mean()
        df['vol_ratio'] = v / vma20
        df['hl_range'] = (df['high'] - df['low']) / c
        if 'amount' in df:
            df['amount_chg'] = df['amount'].astype(float).pct_change(5)
        else:
            df['amount_chg'] = 0.0
        lo20 = c.rolling(20).min(); hi20 = c.rolling(20).max()
        df['close_pos'] = (c - lo20) / (hi20 - lo20).replace(0, np.nan)
        m20 = c.rolling(20).mean(); sd20 = c.rolling(20).std()
        df['boll_width'] = ((m20 + 2 * sd20) - (m20 - 2 * sd20)) / m20
        ema12 = c.ewm(span=12, adjust=False).mean(); ema26 = c.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26; dea = dif.ewm(span=9, adjust=False).mean()
        df['macd_hist'] = (dif - dea) / c
        df['atr_chg'] = (df['high'] - df['low']).rolling(14).mean() / c
        feat_names = ['ret_1', 'ret_3', 'ret_5', 'ret_10', 'ma_diff', 'ma_diff_60',
                      'close_above_ma60', 'rsi', 'vol_chg', 'vol_ratio', 'hl_range',
                      'amount_chg', 'close_pos', 'boll_width', 'macd_hist', 'atr_chg']
        return df, feat_names

    def _collect_symbols(self, limit):
        pairs = []
        for j in self._jobs.values():
            for row in (j.get('long') or []):
                if row.get('代码'):
                    pairs.append((str(row['代码']), str(row.get('名称', ''))))
            for row in (j.get('short') or []):
                if row.get('代码'):
                    pairs.append((str(row['代码']), str(row.get('名称', ''))))
        try:
            for it in self.watch.all():
                c = str(it.get('code', '')).strip()
                if c:
                    pairs.append((c, str(it.get('name', ''))))
        except Exception:
            pass
        seen, sym = set(), []
        for c, n in pairs:
            if c not in seen:
                seen.add(c)
                sym.append((c, n))
        return sym[:int(limit)]

    # ---------------- 全自动交易 ----------------
    def trading_start(self, cfg):
        # 仅在启动成功时落盘，避免校验失败/连接失败反而覆盖已保存的配置
        result = self.trading.start(cfg or {})
        if result.get('ok'):
            _save_trading_config(cfg or {})
        return result

    def trading_get_config(self):
        """返回上次保存的交易配置（股票池/参数），供前端重启后自动恢复表单。"""
        cfg = _load_trading_config()
        cfg.setdefault('stocks', [])
        cfg.setdefault('capital', 100000)
        cfg.setdefault('max_single', 0.2)
        cfg.setdefault('max_total', 0.8)
        cfg.setdefault('stop_loss', 5.0)
        cfg.setdefault('take_profit', 10.0)
        cfg.setdefault('max_daily_trades', 999999)
        cfg.setdefault('max_total', 0.9)
        cfg.setdefault('ai_min_lot', True)
        cfg.setdefault('ai_enabled', False)
        cfg.setdefault('ai_api_key', '')
        cfg.setdefault('ai_api_url', 'https://api.openai.com/v1/chat/completions')
        cfg.setdefault('ai_model', 'gpt-4o-mini')
        return cfg

    def trading_save_config(self, cfg):
        _save_trading_config(cfg or {})
        return {'ok': True, 'msg': '交易配置已保存'}

    def trading_stop(self):
        return self.trading.stop()

    def trading_status(self):
        return self.trading.status()

    def trading_rebalance_now(self):
        """手动触发一轮 资金驱动调仓（预设金额 → 目标组合 → 买卖到目标）。"""
        engine = getattr(self.trading, 'engine', None)
        if engine is None:
            return {'ok': False, 'msg': '引擎未启动，无法调仓'}
        reb = getattr(engine, 'capital_rebalancer', None)
        if reb is None:
            return {'ok': False, 'msg': '未启用资金驱动调仓（勾选「预设资金模式」并启动）'}
        plan = reb.run_rebalance(apply=True)
        return {'ok': True, 'plan': plan,
                'queued': plan.get('queued_actions', 0),
                'msg': '已入队 %d 笔调仓' % plan.get('queued_actions', 0)}

    def trading_picker_candidates(self, source='watch'):
        """实时候选股票池：source='watch'(自选) / 'ranking'(推荐短线榜) / 'mix'(自选+榜单)。"""
        out = []
        def _add(items):
            for it in (items or []):
                c = str(it.get('code') or it.get('代码') or '').strip()
                if c:
                    out.append({'code': c, 'name': str(it.get('name') or it.get('名称') or '')})
        if source in ('watch', 'mix'):
            _add(self.watch.all())
        if source in ('ranking', 'mix'):
            try:
                _add(self.long.screen_shortterm(limit=30))
            except Exception:
                pass
        seen = set(); uniq = []
        for x in out:
            if x['code'] not in seen:
                seen.add(x['code']); uniq.append(x)
        return {'ok': True, 'rows': uniq, 'count': len(uniq)}

    def trading_rebalancer_status(self):
        """资金驱动调仓器 当前状态 / 最近计划。"""
        engine = getattr(self.trading, 'engine', None)
        if engine is None:
            return {'ok': False, 'msg': '引擎未启动'}
        st = engine.get_status().get('rebalancer')
        return {'ok': True, 'rebalancer': st}

    def trading_test_connect(self, cfg):
        return self.trading.test_connect(cfg or {})

    # ---------------- AI 混合策略配置 ----------------
    def ai_strategy_config_save(self, cfg):
        """保存 AI 策略配置到交易配置文件中。"""
        try:
            cfg_data = _load_trading_config() or {}
            c = cfg_data
            c['ai_enabled'] = bool(cfg.get('ai_enabled', False))
            c['ai_api_key'] = str(cfg.get('ai_api_key', '')).strip()
            c['ai_api_url'] = str(cfg.get('ai_api_url', 'https://api.openai.com/v1/chat/completions')).strip()
            c['ai_model'] = str(cfg.get('ai_model', 'gpt-4o-mini')).strip()
            _save_trading_config(c)
            return {'ok': True, 'msg': 'AI策略配置已保存'}
        except Exception as e:
            return {'ok': False, 'msg': str(e)}

    def ai_strategy_config_get(self):
        """读取已保存的 AI 策略配置。"""
        try:
            c = _load_trading_config() or {}
            return {
                'ok': True,
                'ai_enabled': bool(c.get('ai_enabled', False)),
                'ai_api_key': str(c.get('ai_api_key', '')),
                'ai_api_url': str(c.get('ai_api_url', 'https://api.openai.com/v1/chat/completions')),
                'ai_model': str(c.get('ai_model', 'gpt-4o-mini')),
                'hybrid_available': HAS_HYBRID_AI,
            }
        except Exception as e:
            return {'ok': False, 'msg': str(e)}

    def ai_strategy_status(self):
        """查看当前引擎的 AI 策略运行状态。"""
        engine = getattr(self.trading, 'engine', None)
        if engine is None:
            return {'ok': False, 'msg': '引擎未启动，请先启动交易引擎'}
        ai_strat = getattr(engine, 'ai_strategy', None)
        if ai_strat is None:
            return {'ok': False, 'msg': '未加载AI策略'}
        try:
            st = ai_strat.get_status() if hasattr(ai_strat, 'get_status') else {}
            return {'ok': True, 'status': st}
        except Exception as e:
            return {'ok': False, 'msg': str(e)}

    def trading_reset_account(self):
        return self.trading.reset_account()

    def trading_returns(self):
        """收益视图数据（模拟账户汇总 + 资产曲线 + 分股盈亏 + 最近交易）"""
        api = getattr(self.trading, 'trading_api', None)
        if api is None or not hasattr(api, 'get_returns_data'):
            from stock_trading_api import TradingAPIFactory
            cfg = _load_trading_config()
            cap = float(cfg.get('capital') or 100000)
            api = TradingAPIFactory.create_api('simulated', initial_balance=cap)
            self.trading.trading_api = api
        try:
            return api.get_returns_data()
        except Exception as e:
            return {'ok': False, 'msg': '获取收益数据失败: %s' % e}

    def detect_ths_exe(self):
        import glob
        cands = [
            r'C:\同花顺\xiadan.exe',
            r'C:\同花顺\xiadan\xiadan.exe',
        ]
        for c in cands:
            if os.path.exists(c):
                return c
        home = os.path.expanduser('~')
        for pattern in [
            r'C:\*\xiadan.exe',
            r'C:\*\*\xiadan.exe',
            os.path.join(home, 'Downloads', '*', 'xiadan.exe'),
            os.path.join(home, 'Downloads', 'xiadan.exe'),
            os.path.join(home, 'Desktop', '*', 'xiadan.exe'),
        ]:
            hits = glob.glob(pattern)
            if hits:
                return hits[0]
        return ''

    # ============================ 全球证券（港股/美股预留）============================
    def _gs(self):
        if self.global_sec is None:
            return {'ok': False, 'msg': '全球证券预留接口未加载'}
        return self.global_sec

    def gs_markets(self):
        """所有市场状态列表（A股/港股/美股）"""
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        return {'ok': True, 'markets': gs.markets()}

    def gs_market_status(self, market='hk'):
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        return gs.market_status(str(market))

    def gs_set_account_opened(self, market, opened, broker='', notes=''):
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        return gs.set_account_opened(str(market), bool(opened),
                                     broker=str(broker or ''), notes=str(notes or ''))

    def gs_realtime(self, codes, market='hk'):
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        if isinstance(codes, str):
            import re as _re
            codes = [c.strip() for c in _re.split(r'[,，;\s]+', codes) if c.strip()]
        return gs.realtime(codes or [], market=str(market))

    def gs_history(self, code, market='hk', years=2):
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        try:
            years = int(years)
        except Exception:
            years = 2
        r = gs.history(code, market=str(market), years=years)
        # 转成与 query_kline 兼容的 kline 结构，方便前端直接画
        kline = []
        for row in (r.get('rows') or []):
            if not isinstance(row, dict):
                continue
            kline.append({
                'd': str(row.get('日期') or row.get('date') or ''),
                'o': float(row.get('开盘') or row.get('open') or 0),
                'h': float(row.get('最高') or row.get('high') or 0),
                'l': float(row.get('最低') or row.get('low') or 0),
                'c': float(row.get('收盘') or row.get('close') or 0),
                'v': float(row.get('成交量') or row.get('volume') or 0),
            })
        return {'ok': bool(r.get('ok')), 'kline': kline,
                'name': str(code), 'msg': r.get('msg', '')}

    def gs_financial_report(self, code, market='hk'):
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        r = gs.financial_report(code, market=str(market))
        rows = r.get('rows') or []
        return {'ok': bool(r.get('ok')), 'rows': rows[:20],
                'msg': r.get('msg', '')}

    def gs_news(self, code, market='hk', limit=20):
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        try:
            limit = int(limit)
        except Exception:
            limit = 20
        r = gs.news(code, market=str(market), limit=limit)
        rows = r.get('rows') or []
        return {'ok': bool(r.get('ok')), 'rows': rows[:limit],
                'msg': r.get('msg', '')}

    def gs_positions(self, market=''):
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        m = str(market) if market else None
        data = gs.positions(m)
        if m:
            return {'ok': True, 'positions': (data or {}).get('positions', []),
                    'account_opened': (data or {}).get('account_opened', False),
                    'currency': (data or {}).get('currency', '')}
        return {'ok': True, 'markets': {k: v for k, v in (data or {}).items()}}

    def gs_add_position(self, market, code, name, volume, avg_price=0.0):
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        try:
            volume = float(volume)
        except Exception:
            volume = 0.0
        try:
            avg_price = float(avg_price)
        except Exception:
            avg_price = 0.0
        return gs.add_position(str(market), str(code), str(name or code),
                               volume, avg_price=avg_price)

    def gs_remove_position(self, market, code):
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        return gs.remove_position(str(market), str(code))

    # ---- 信息差 / 每日财报（与自选 + 关注板块强关联）----
    def info_gap_daily(self, push=True, sector_names=None, market_filter=''):
        """每日财报 + 信息差聚合。

        强关联逻辑：
          - 自选：自动取 watch 里 market == 'hk' 或 'us' 的代码（或全部）
          - 关注板块：前端传入 sector_names，写入报告，后续可据此过滤新闻
          - market_filter: 'a' / 'hk' / 'us' / ''(全部)，决定取哪些自选
        """
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        mf = str(market_filter) if market_filter else ''
        codes = [i['code'] for i in self.watch.by_market(mf)] if mf else \
                [i['code'] for i in self.watch.all()]
        # 把自选里的港美股都喂进去（财报 / 信息差只对港美股生效）
        hk_us = [i['code'] for i in self.watch.all()
                 if i.get('market') in ('hk', 'us')]
        target = hk_us if hk_us else codes
        return gs.daily_digest(watchlist_codes=target,
                               sector_names=sector_names,
                               push=bool(push))

    def info_gap_announcements(self, codes, limit=20):
        """重大公告列表（自选 + 关注板块成分股）"""
        gs = self._gs()
        if isinstance(gs, dict):
            return gs
        if isinstance(codes, str):
            import re as _re
            codes = [c.strip() for c in _re.split(r'[,，;\s]+', codes) if c.strip()]
        return gs.daily_digest(watchlist_codes=codes or [],
                               sector_names=[], push=False)

    # ---- 自选股：支持港美股市场 ----
    def watch_add_market(self, code, name, market='a'):
        ok, msg = self.watch.add(code, name, market=market)
        return {'ok': ok, 'msg': msg}

    def watch_del_market(self, code, market='a'):
        ok, msg = self.watch.remove(code, market=market)
        return {'ok': ok, 'msg': msg}

    def watch_clear_market(self, market=''):
        ok, msg = self.watch.remove_all(market)
        return {'ok': ok, 'msg': msg}

    def watch_list_market(self, market=''):
        """按市场返回自选。market: 'a'/'hk'/'us'/''(全部)"""
        items = self.watch.by_market(market)
        return items

    def open_legacy(self):
        """打开旧版 Tkinter 完整界面（独立进程），保留回测/基金/板块等完整功能。"""
    def open_legacy(self):
        """打开旧版 Tkinter 完整界面（独立进程），保留回测/基金/板块等完整功能。"""
        try:
            import subprocess
            base = os.path.dirname(os.path.abspath(__file__))
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, '--legacy']
                cwd = base
            else:
                cmd = [sys.executable, os.path.join(base, 'main_web.py'), '--legacy']
                cwd = base
            subprocess.Popen(cmd, cwd=cwd)
            return {'ok': True, 'msg': '已打开旧版完整界面'}
        except Exception as e:
            return {'ok': False, 'msg': '打开失败: %s' % e}


def main():
    # 无头 24h 服务模式：--server [--host 0.0.0.0] [--port 8000] [--token 令牌]
    if '--server' in sys.argv:
        from headless_server import run_server
        argv = sys.argv[1:]
        host, port, token = '0.0.0.0', 8000, os.environ.get('AITRADE_TOKEN')
        for i, a in enumerate(argv):
            if a in ('--host',) and i + 1 < len(argv):
                host = argv[i + 1]
            elif a in ('--port',) and i + 1 < len(argv):
                port = int(argv[i + 1])
            elif a in ('--token',) and i + 1 < len(argv):
                token = argv[i + 1]
        run_server(host=host, port=port, token=token)
        return

    api = WebApi()
    if HAS_WEBVIEW:
        try:
            html_path = os.path.abspath(resource_path(os.path.join('web', 'index.html')))
            window = webview.create_window(
                'AI 量化交易系统',
                url=html_path,
                js_api=api,
                width=1280,
                height=820,
                min_size=(1080, 700),
                background_color='#0f1420',
            )
            webview.start(debug=False)
            return
        except Exception as e:
            print('桌面窗口模式启动失败: %s' % e)
            print('改用本地界面模式...')

    # 回退：本地 HTTP 服务 + 浏览器应用窗口（零依赖，Win10/11 自带 Edge）
    from headless_server import serve_local
    serve_local(host='127.0.0.1', port=8899, open_browser=True)


if __name__ == '__main__':
    main()
