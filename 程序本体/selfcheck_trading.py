# -*- coding: utf-8 -*-
"""
Read-only self check for the AI quant trading system.

Run:  python selfcheck_trading.py

It never places a real order and never opens the broker client. It verifies:
  1. imports / dependency versions
  2. easytrader broker-name mapping used by EasyTraderAPI
  3. EasyTraderAPI adapter contract against a fake broker client
  4. broker client (xiadan.exe) detection + saved trading config
  5. live quote lookup through SmartDataClient
  6. headless web server boot + API endpoints
"""
import os
import sys
import json
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok), detail))
    print(('[PASS] ' if ok else '[FAIL] ') + name + ((' :: ' + str(detail)) if detail else ''))


def section(title):
    print('\n=== %s ===' % title)


# --------------------------------------------------------------------------
# 1. imports / versions
# --------------------------------------------------------------------------
section('1. imports')
try:
    import easytrader
    check('import easytrader', True, 'version=%s' % getattr(easytrader, '__version__', '?'))
except Exception as e:
    check('import easytrader', False, e)

for mod in ('pandas', 'numpy', 'requests', 'pywintypes'):
    try:
        __import__(mod)
        check('import %s' % mod, True)
    except Exception as e:
        check('import %s' % mod, False, e)

try:
    from stock_trading_api import EasyTraderAPI, TradingAPIFactory, Order  # noqa: F401
    from auto_trading_engine import AutoTradingEngine, MockAIStrategy, TradingSignal  # noqa: F401
    check('import trading modules', True)
except Exception as e:
    check('import trading modules', False, repr(e))
    print('\n'.join('%s %s' % ('[FAIL]' if not ok else '[PASS]', n) for n, ok, _ in RESULTS))
    sys.exit(1)


# --------------------------------------------------------------------------
# 2. broker mapping
# --------------------------------------------------------------------------
section('2. broker mapping')
for alias, expected in (('universal', 'universal_client'), ('ths', 'ths'), ('gj', 'gj_client')):
    api = EasyTraderAPI(broker=alias)
    check('alias %s -> %s' % (alias, expected), api.broker == expected, 'got %s' % api.broker)

try:
    trader = easytrader.use('universal_client')
    need = ('prepare', 'buy', 'sell', 'market_buy', 'market_sell',
            'cancel_entrust', 'cancel_all_entrusts', 'exit')
    missing = [m for m in need if not hasattr(trader, m)]
    props = ('balance', 'position', 'today_entrusts', 'today_trades')
    missing_props = [p for p in props if not hasattr(type(trader), p)]
    check('universal_client api surface', not missing and not missing_props,
          'missing methods=%s missing props=%s' % (missing, missing_props))
except Exception as e:
    check('universal_client api surface', False, repr(e))


# --------------------------------------------------------------------------
# 3. adapter contract against a fake broker client
# --------------------------------------------------------------------------
section('3. adapter contract (fake client, no real order)')


class FakeTrader:
    """Mimics the dict shapes returned by easytrader's universal client."""

    def __init__(self):
        self.balance = {
            '资金余额': 50000.0,
            '可用金额': 48000.0,
            '可取金额': 47000.0,
            '总资产': 62000.0,
        }
        self.position = [{
            '证券代码': '000858',
            '证券名称': '五粮液',
            '股票余额': 200,
            '可用余额': 200,
            '参考成本价': 146.39,
            '市价': 149.06,
            '股票市值': 29812.0,
            '参考盈亏': 534.0,
            '盈亏比例(%)': 1.82,
        }]
        self.today_entrusts = [
            {'委托编号': '1001', '证券代码': '000858', '状态': '已成',
             '委托价格': 149.0, '委托数量': 200, '证券名称': '五粮液'},
            {'委托编号': '1002', '证券代码': '600519', '状态': '已报',
             '委托价格': 1700.0, '委托数量': 100, '证券名称': '贵州茅台'},
        ]
        self.today_trades = [{
            '成交编号': '9001',
            '发生日期': '2026-08-06',
            '证券代码': '000858',
            '证券名称': '五粮液',
            '操作': '证券买入',
            '成交价格': 146.39,
            '成交数量': 200,
            '成交金额': 29278.0,
        }]
        self.calls = []
        self.exited = False

    def buy(self, security, price, amount, **kwargs):
        self.calls.append(('buy', security, price, amount))
        return {'entrust_no': '2001'}

    def sell(self, security, price, amount, **kwargs):
        self.calls.append(('sell', security, price, amount))
        return {'entrust_no': '2002'}

    def market_buy(self, security, amount, **kwargs):
        self.calls.append(('market_buy', security, amount))
        return {'message': 'success'}

    def market_sell(self, security, amount, **kwargs):
        self.calls.append(('market_sell', security, amount))
        return {'message': 'success'}

    def cancel_entrust(self, entrust_no):
        return {'message': 'success'}

    def cancel_all_entrusts(self):
        return None

    def exit(self):
        self.exited = True


fake = FakeTrader()
api = EasyTraderAPI(broker='universal', exe_path='X:\\nonexistent\\xiadan.exe')
api._trader = fake
api.connected = True

bal = api.get_account_balance()
check('balance parsing', bal.get('balance') == 48000.0 and bal.get('total_assets') == 62000.0,
      'balance=%s total_assets=%s positions_value=%s' % (
          bal.get('balance'), bal.get('total_assets'), bal.get('positions_value')))
check('balance positions_value fallback',
      abs(bal.get('positions_value', 0) - 14000.0) < 0.01, bal.get('positions_value'))

pos = api.get_positions()
check('position parsing', len(pos) == 1 and pos[0]['stock_code'] == '000858'
      and abs(pos[0]['volume'] - 2.0) < 0.01,
      pos[0] if pos else 'empty')

limit_order = api.buy('600519', 1700.0, 1)
check('buy(1 hand) -> 100 shares sent', fake.calls[-1] == ('buy', '600519', 1700.0, 100),
      fake.calls[-1])
check('buy order wrapped', limit_order.order_id == '2001' and limit_order.status == 'SUBMITTED',
      'id=%s status=%s' % (limit_order.order_id, limit_order.status))

market_order = api.buy('600519', 0, 2, order_type='MARKET')
check('market buy -> shares', fake.calls[-1] == ('market_buy', '600519', 200), fake.calls[-1])
check('market buy wrapped', market_order.status == 'SUBMITTED',
      'id=%s status=%s' % (market_order.order_id, market_order.status))

sell_order = api.sell('000858', 149.0, 2)
check('sell(2 hands) -> 200 shares sent', fake.calls[-1] == ('sell', '000858', 149.0, 200),
      fake.calls[-1])
check('sell order wrapped', sell_order.order_id == '2002', sell_order.order_id)

open_orders = api.get_open_orders()
check('open orders filter (exclude cheng)', len(open_orders) == 1
      and open_orders[0].stock_code == '600519', len(open_orders))

history = api.get_trade_history()
check('trade history parsing', len(history) == 1 and history[0]['side'] == 'BUY'
      and history[0]['volume'] == 200, history[0] if history else 'empty')

api.disconnect()
check('disconnect calls exit()', fake.exited)


# --------------------------------------------------------------------------
# 3b. engine bookkeeping for real (SUBMITTED) orders
# --------------------------------------------------------------------------
section('3b. engine bookkeeping for real (SUBMITTED) orders')


class FakeOrder:
    def __init__(self, order_id, status, message=''):
        self.order_id = order_id
        self.status = status
        self.message = message
        self.filled_volume = 0
        self.filled_price = 0.0


class FakeRealAPI:
    """Real-broker-like API: orders come back as SUBMITTED with an entrust number."""

    def __init__(self, balance=100000.0):
        self.balance = balance
        self.orders = []

    def get_real_time_price(self, code):
        return {'stock_code': code, 'stock_name': 'test', 'price': 10.0, 'update_time': ''}

    def get_account_balance(self):
        return {'balance': self.balance, 'total_assets': self.balance,
                'positions_value': 0.0, 'initial_balance': self.balance}

    def get_positions(self):
        return []

    def buy(self, stock_code, price, volume, order_type='MARKET'):
        self.orders.append(('BUY', stock_code, volume, order_type))
        return FakeOrder('9001', 'SUBMITTED')

    def sell(self, stock_code, price, volume, order_type='MARKET'):
        self.orders.append(('SELL', stock_code, volume, order_type))
        return FakeOrder('9002', 'SUBMITTED')


real_api = FakeRealAPI()
engine = AutoTradingEngine(real_api, MockAIStrategy(stocks=['600519']), allow_off_hours=True)
engine.set_risk_config(max_single_position_ratio=0.5, max_total_position_ratio=0.9)
engine._execute_buy(TradingSignal('600519', 'BUY', 0.9), None)
check('SUBMITTED order counted as a trade', engine.daily_trades == 1,
      'daily_trades=%s orders=%s' % (engine.daily_trades, real_api.orders))
check('SUBMITTED order logged as accepted',
      any('委托已提交' in e['message'] for e in engine.trade_logs),
      engine.trade_logs[-1]['message'] if engine.trade_logs else 'no log')

real_api.balance = 0.0
engine.daily_trades = 0
engine._execute_buy(TradingSignal('600519', 'BUY', 0.9), None)
check('no order placed with zero balance',
      len(real_api.orders) == 1 and engine.daily_trades == 0,
      'orders=%s daily_trades=%s' % (len(real_api.orders), engine.daily_trades))


# --------------------------------------------------------------------------
# 3c. real-mode guard against the random mock strategy
# --------------------------------------------------------------------------
section('3c. real-mode guard against random mock strategy')
from AI量化交易系统Web import TradingController  # noqa: E402

controller = TradingController()
guard = controller.start({'mode': 'easytrader', 'exe_path': 'X:\\nope\\xiadan.exe',
                          'stocks': ['600519']})
check('real mode blocked without explicit opt-in',
      (not guard.get('ok')) and 'allow_mock_strategy' not in guard.get('msg', '')
      and ('勾选' in guard.get('msg', '')), guard.get('msg'))


# --------------------------------------------------------------------------
# 4. client detection + saved config
# --------------------------------------------------------------------------
section('4. broker client detection + saved config')
from AI量化交易系统Web import TradingController  # noqa: E402

detected = TradingController._detect_ths_exe()
check('detect xiadan.exe', bool(detected), detected or 'not found')

cfg_path = os.path.join(BASE, 'trading_config.json')
if os.path.exists(cfg_path):
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    mode = str(cfg.get('mode', ''))
    if mode == 'easytrader':
        check('saved trading mode', True, 'mode=easytrader (real trading configured)')
    else:
        print('[INFO] saved trading mode = %s -> real trading not configured yet' % mode)
else:
    print('[INFO] trading_config.json not found')

state_path = os.path.join(BASE, 'engine_state.json')
check('engine auto-resume state', True,
      'engine_state.json present' if os.path.exists(state_path)
      else 'no engine_state.json (auto-resume idle)')


# --------------------------------------------------------------------------
# 5. live quote lookup
# --------------------------------------------------------------------------
section('5. live quote lookup')
try:
    from 智能数据查询 import SmartDataClient  # noqa: E402
    client = SmartDataClient()
    df = client.get_realtime(['600519'])
    ok = df is not None and not df.empty and float(df.iloc[0].get('price', 0) or 0) > 0
    check('realtime quote 600519', ok,
          'price=%s name=%s' % (df.iloc[0].get('price'), df.iloc[0].get('name')) if ok else 'empty')
except Exception as e:
    check('realtime quote 600519', False, repr(e))


# --------------------------------------------------------------------------
# 6. headless server + endpoints
# --------------------------------------------------------------------------
section('6. headless server + endpoints')
import urllib.request  # noqa: E402

PORT = 8011
try:
    from headless_server import start_server  # noqa: E402
    r = start_server('127.0.0.1', PORT, None)
    check('server boot', r.get('ok'), r.get('msg'))
    threading.Event().wait(1)
    for ep in ('ping', 'trading_status', 'trading_get_config', 'watch_list', 'portfolio_get'):
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d/api/%s' % (PORT, ep), timeout=30) as resp:
                body = json.loads(resp.read().decode('utf-8'))
            check('GET /api/%s' % ep, True, json.dumps(body, ensure_ascii=False)[:160])
        except Exception as e:
            check('GET /api/%s' % ep, False, repr(e))
    for ep in ('index.html', 'app.js', 'style.css'):
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d/%s' % (PORT, ep), timeout=20) as resp:
                check('GET /%s' % ep, resp.status == 200, 'len=%s' % len(resp.read()))
        except Exception as e:
            check('GET /%s' % ep, False, repr(e))
    try:
        payload = json.dumps({'args': [{'mode': 'easytrader', 'exe_path': 'X:\\nope\\xiadan.exe',
                                        'stocks': ['600519']}]}).encode('utf-8')
        req = urllib.request.Request('http://127.0.0.1:%d/api/trading_start' % PORT, data=payload,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode('utf-8'))
        check('POST /api/trading_start blocked without opt-in',
              (not body.get('ok')) and ('勾选' in str(body.get('msg', ''))), body.get('msg'))
    except Exception as e:
        check('POST /api/trading_start blocked without opt-in', False, repr(e))
except Exception as e:
    check('server boot', False, repr(e))


section('summary')
failed = [n for n, ok, _ in RESULTS if not ok]
print('total=%d passed=%d failed=%d' % (len(RESULTS), len(RESULTS) - len(failed), len(failed)))
if failed:
    print('failed checks:')
    for n in failed:
        print('  - %s' % n)
sys.exit(1 if failed else 0)
