"""
股票交易API接口框架
支持模拟交易和真实交易模式
提供统一的交易接口，便于扩展真实券商API
"""

import os
import json
import time
import hashlib
from datetime import datetime
import pandas as pd
from abc import ABC, abstractmethod

# 交易类型
ORDER_TYPE = {
    'MARKET': '市价单',
    'LIMIT': '限价单',
    'STOP': '止损单',
    'STOP_LIMIT': '限价止损单'
}

# 交易方向
ORDER_SIDE = {
    'BUY': '买入',
    'SELL': '卖出'
}

# 订单状态
ORDER_STATUS = {
    'PENDING': '待提交',
    'SUBMITTED': '已提交',
    'FILLED': '已成交',
    'PARTIALLY_FILLED': '部分成交',
    'CANCELLED': '已取消',
    'REJECTED': '已拒绝'
}


class Order:
    """订单类"""
    
    def __init__(self, order_id, stock_code, stock_name, side, order_type, 
                 price, volume, create_time=None):
        self.order_id = order_id
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.side = side  # BUY or SELL
        self.order_type = order_type  # MARKET, LIMIT, STOP, STOP_LIMIT
        self.price = price
        self.volume = volume  # 手数
        self.filled_volume = 0
        self.filled_price = 0.0
        self.status = 'PENDING'
        self.create_time = create_time or datetime.now()
        self.update_time = self.create_time
        self.message = ''
    
    def fill(self, filled_volume, filled_price):
        """成交订单"""
        self.filled_volume = filled_volume
        self.filled_price = filled_price
        self.status = 'FILLED' if filled_volume == self.volume else 'PARTIALLY_FILLED'
        self.update_time = datetime.now()
    
    def cancel(self):
        """取消订单"""
        self.status = 'CANCELLED'
        self.update_time = datetime.now()
    
    def reject(self, message=''):
        """拒绝订单"""
        self.status = 'REJECTED'
        self.message = message
        self.update_time = datetime.now()
    
    def submit(self):
        """提交订单"""
        self.status = 'SUBMITTED'
        self.update_time = datetime.now()
    
    def to_dict(self):
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'side': self.side,
            'order_type': self.order_type,
            'price': self.price,
            'volume': self.volume,
            'filled_volume': self.filled_volume,
            'filled_price': self.filled_price,
            'status': self.status,
            'status_text': ORDER_STATUS.get(self.status, self.status),
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': self.message
        }


class TradingAPI(ABC):
    """交易API抽象基类"""
    
    @abstractmethod
    def buy(self, stock_code, price, volume, order_type='MARKET'):
        """买入股票"""
        pass
    
    @abstractmethod
    def sell(self, stock_code, price, volume, order_type='MARKET'):
        """卖出股票"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id):
        """取消订单"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id):
        """获取订单状态"""
        pass
    
    @abstractmethod
    def get_open_orders(self):
        """获取所有未成交订单"""
        pass
    
    @abstractmethod
    def get_account_balance(self):
        """获取账户资金"""
        pass
    
    @abstractmethod
    def get_positions(self):
        """获取持仓"""
        pass
    
    @abstractmethod
    def get_trade_history(self, start_date=None, end_date=None):
        """获取交易历史"""
        pass
    
    @abstractmethod
    def get_real_time_price(self, stock_code):
        """获取实时价格"""
        pass


class SimulatedTradingAPI(TradingAPI):
    """模拟交易API"""
    
    def __init__(self, initial_balance=100000.0, data_source=None):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions = {}  # stock_code -> {'name', 'volume', 'avg_cost', 'current_price'}
        self.orders = {}  # order_id -> Order
        self.trade_history = []
        self.data_source = data_source
        self.order_counter = 0
        
        # 加载历史数据
        self._load_data()
        # T+1：记录当日买入量，用于限制当日卖出
        self._today = datetime.now().date()
        for p in self.positions.values():
            p.setdefault('today_buys', 0)

    def _rollover_t1(self):
        """跨日后重置当日买入量（T+1 的可卖数恢复为全部持仓）"""
        today = datetime.now().date()
        if getattr(self, '_today', None) != today:
            for p in self.positions.values():
                p['today_buys'] = 0
            self._today = today
    
    def _load_data(self):
        """加载历史数据"""
        # 尝试加载账户状态
        try:
            if os.path.exists('simulated_account.json'):
                with open('simulated_account.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stored_initial = data.get('initial_balance', data.get('balance'))
                    # 若指定了新初始资金且与已保存的不一致，则按新本金重新开户（清空旧记录）
                    if stored_initial is not None and abs(float(stored_initial) - float(self.initial_balance)) > 0.01:
                        self.balance = float(self.initial_balance)
                        self.positions = {}
                        self.trade_history = []
                        self.returns_history = []
                        self._save_data()
                        print(f"[OK] 初始资金已调整为 {self.initial_balance:,.2f}，模拟账户已重置")
                    else:
                        self.balance = data.get('balance', self.initial_balance)
                        self.positions = data.get('positions', {})
                        self.trade_history = data.get('trade_history', []) or []
                        self.returns_history = data.get('returns_history', []) or []
                        print(f"[OK] 已加载模拟账户数据，余额: {self.balance:,.2f}")
        except Exception as e:
            print(f"[WARN] 加载模拟账户数据失败: {e}")
    
    def _save_data(self):
        """保存账户状态（含交易历史与资产快照）"""
        try:
            self.record_snapshot()
            data = {
                'initial_balance': self.initial_balance,
                'balance': self.balance,
                'positions': self.positions,
                'trade_history': self.trade_history,
                'returns_history': getattr(self, 'returns_history', []),
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open('simulated_account.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存模拟账户数据失败: {e}")

    def record_snapshot(self):
        """记录一条账户资产快照（用于收益视图的资产曲线），不改变交易行为"""
        try:
            acc = self.get_account_balance()
            snap = {
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'balance': round(acc['balance'], 2),
                'positions_value': round(acc['positions_value'], 2),
                'total_assets': round(acc['total_assets'], 2),
            }
            hist = self.__dict__.setdefault('returns_history', [])
            if not hist or hist[-1].get('date') != snap['date']:
                hist.append(snap)
                if len(hist) > 20000:
                    del hist[:len(hist) - 20000]
        except Exception:
            pass
    
    def _generate_order_id(self):
        """生成唯一订单ID"""
        self.order_counter += 1
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"SIM_{timestamp}_{self.order_counter:04d}"
    
    def _get_stock_name(self, stock_code):
        """获取股票名称"""
        stock_names = {
            '000001': '平安银行',
            '000002': '万科A',
            '000333': '美的集团',
            '000651': '格力电器',
            '600000': '浦发银行',
            '600519': '贵州茅台',
            '601318': '中国平安',
            '600036': '招商银行',
            '000858': '五粮液',
            '002594': '比亚迪'
        }
        return stock_names.get(stock_code, f"股票{stock_code}")
    
    def _get_current_price(self, stock_code):
        """获取当前价格（模拟，同一分钟内保持稳定，避免各检查点价格不一致）"""
        cache = self.__dict__.setdefault('_price_cache', {})
        key = datetime.now().strftime('%Y%m%d%H%M')
        hit = cache.get(stock_code)
        if hit and hit[0] == key:
            return hit[1]
        price = self._compute_price(stock_code)
        cache[stock_code] = (key, price)
        return price

    def _compute_price(self, stock_code):
        """计算模拟价格"""
        # 优先从数据源获取
        if self.data_source:
            try:
                df = self.data_source.get_stock_realtime([stock_code])
                if not df.empty:
                    return df.iloc[0].get('最新价', 10.0)
            except:
                pass

        # 模拟价格波动
        if stock_code in self.positions:
            base_price = self.positions[stock_code]['avg_cost']
        else:
            # 默认价格
            default_prices = {
                '000001': 10.50,
                '000002': 15.80,
                '000333': 58.20,
                '000651': 42.50,
                '600000': 8.30,
                '600519': 1680.00,
                '601318': 48.60,
                '600036': 35.20,
                '000858': 145.00,
                '002594': 268.00
            }
            base_price = default_prices.get(stock_code, 10.0)

        # 添加随机波动 (-2% ~ +2%)
        import random
        fluctuation = (random.random() - 0.5) * 0.04
        return base_price * (1 + fluctuation)
    
    def buy(self, stock_code, price, volume, order_type='MARKET'):
        """买入股票"""
        self._rollover_t1()
        # 获取当前价格
        current_price = self._get_current_price(stock_code)
        
        # 市价单使用当前价格
        if order_type == 'MARKET':
            execute_price = current_price
        else:
            execute_price = price
        
        # 计算成本
        cost = execute_price * volume * 100  # 1手=100股
        
        if cost > self.balance:
            order = Order(
                order_id=self._generate_order_id(),
                stock_code=stock_code,
                stock_name=self._get_stock_name(stock_code),
                side='BUY',
                order_type=order_type,
                price=execute_price,
                volume=volume
            )
            order.reject(f"余额不足: 需要 {cost:.2f}，可用 {self.balance:.2f}")
            self.orders[order.order_id] = order
            return order
        
        # 创建订单
        order = Order(
            order_id=self._generate_order_id(),
            stock_code=stock_code,
            stock_name=self._get_stock_name(stock_code),
            side='BUY',
            order_type=order_type,
            price=execute_price,
            volume=volume
        )
        order.submit()
        
        # 模拟成交（市价单立即成交）
        if order_type == 'MARKET':
            time.sleep(0.1)  # 模拟网络延迟
            order.fill(volume, execute_price)
            
            # 更新持仓
            if stock_code in self.positions:
                pos = self.positions[stock_code]
                total_cost = pos['avg_cost'] * pos['volume'] + cost
                pos['volume'] += volume
                pos['avg_cost'] = total_cost / pos['volume']
            else:
                self.positions[stock_code] = {
                    'name': self._get_stock_name(stock_code),
                    'volume': volume,
                    'avg_cost': execute_price,
                    'current_price': execute_price
                }
            self.positions[stock_code]['today_buys'] = self.positions[stock_code].get('today_buys', 0) + volume
            
            # 扣除资金
            self.balance -= cost
            
            # 记录交易历史
            self.trade_history.append({
                'trade_id': order.order_id,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stock_code': stock_code,
                'stock_name': self._get_stock_name(stock_code),
                'side': 'BUY',
                'price': execute_price,
                'volume': volume,
                'amount': cost
            })
            
            print(f"[OK] 买入成功: {stock_code} {volume}手 @ {execute_price:.2f}")
        
        self.orders[order.order_id] = order
        self._save_data()
        
        return order
    
    def sell(self, stock_code, price, volume, order_type='MARKET'):
        """卖出股票"""
        self._rollover_t1()
        # 检查持仓
        if stock_code not in self.positions:
            order = Order(
                order_id=self._generate_order_id(),
                stock_code=stock_code,
                stock_name=self._get_stock_name(stock_code),
                side='SELL',
                order_type=order_type,
                price=price,
                volume=volume
            )
            order.reject("未持有该股票")
            self.orders[order.order_id] = order
            return order
        
        pos = self.positions[stock_code]
        if volume > pos['volume']:
            order = Order(
                order_id=self._generate_order_id(),
                stock_code=stock_code,
                stock_name=self._get_stock_name(stock_code),
                side='SELL',
                order_type=order_type,
                price=price,
                volume=volume
            )
            order.reject(f"持仓不足: 持有 {pos['volume']} 手，要卖 {volume} 手")
            self.orders[order.order_id] = order
            return order
        
        # T+1：当日买入的份额不可当日卖出
        sellable = max(0, pos['volume'] - pos.get('today_buys', 0))
        if sellable <= 0:
            order = Order(
                order_id=self._generate_order_id(),
                stock_code=stock_code,
                stock_name=self._get_stock_name(stock_code),
                side='SELL',
                order_type=order_type,
                price=price,
                volume=volume
            )
            order.reject(f"T+1 限制: {stock_code} 全部为当日买入，当天不可卖出")
            self.orders[order.order_id] = order
            return order
        clipped_note = ''
        if volume > sellable:
            clipped_note = f"（另有 {volume - sellable} 手为当日买入，T+1 不可卖）"
            volume = sellable
            order = Order(
                order_id=self._generate_order_id(),
                stock_code=stock_code,
                stock_name=self._get_stock_name(stock_code),
                side='SELL',
                order_type=order_type,
                price=price,
                volume=volume
            )
        else:
            order = Order(
                order_id=self._generate_order_id(),
                stock_code=stock_code,
                stock_name=self._get_stock_name(stock_code),
                side='SELL',
                order_type=order_type,
                price=price,
                volume=volume
            )
        
        # 获取当前价格
        current_price = self._get_current_price(stock_code)
        
        # 市价单使用当前价格
        if order_type == 'MARKET':
            execute_price = current_price
        else:
            execute_price = price
        
        # 创建订单
        order = Order(
            order_id=self._generate_order_id(),
            stock_code=stock_code,
            stock_name=self._get_stock_name(stock_code),
            side='SELL',
            order_type=order_type,
            price=execute_price,
            volume=volume
        )
        order.submit()
        
        # 模拟成交
        if order_type == 'MARKET':
            time.sleep(0.1)  # 模拟网络延迟
            order.fill(volume, execute_price)
            
            # 计算收益
            revenue = execute_price * volume * 100
            cost = pos['avg_cost'] * volume * 100
            profit = revenue - cost
            profit_pct = profit / cost * 100 if cost > 0 else 0
            
            # 更新持仓
            pos['volume'] -= volume
            if pos['volume'] == 0:
                del self.positions[stock_code]
            
            # 增加资金
            self.balance += revenue
            
            # 记录交易历史
            self.trade_history.append({
                'trade_id': order.order_id,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stock_code': stock_code,
                'stock_name': self._get_stock_name(stock_code),
                'side': 'SELL',
                'price': execute_price,
                'volume': volume,
                'amount': revenue,
                'profit': profit,
                'profit_pct': profit_pct
            })
            
            print(f"[OK] 卖出成功: {stock_code} {volume}手 @ {execute_price:.2f}")
            print(f"   收益: {profit:+.2f} ({profit_pct:+.2f}%)")
            if clipped_note:
                print(f"[T+1] {clipped_note}")
        
        self.orders[order.order_id] = order
        self._save_data()
        
        return order
    
    def cancel_order(self, order_id):
        """取消订单"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in ['PENDING', 'SUBMITTED']:
                order.cancel()
                print(f"[OK] 订单已取消: {order_id}")
                return True
            else:
                print(f"[WARN] 订单状态不允许取消: {order.status}")
        return False
    
    def get_order_status(self, order_id):
        """获取订单状态"""
        return self.orders.get(order_id)
    
    def get_open_orders(self):
        """获取所有未成交订单"""
        return [order for order in self.orders.values() 
                if order.status in ['PENDING', 'SUBMITTED', 'PARTIALLY_FILLED']]
    
    def get_account_balance(self):
        """获取账户资金"""
        # 计算总资产（注意：持仓字典以 stock_code 为键）
        total_assets = self.balance
        for stock_code, pos in self.positions.items():
            pos['current_price'] = self._get_current_price(stock_code)
            total_assets += pos['current_price'] * pos['volume'] * 100
        
        # 计算持仓市值
        positions_value = total_assets - self.balance
        
        # 计算总盈亏（总资产 - 初始资金；已实现盈亏已含在 balance 中）
        cost_basis = self.initial_balance
        profit = total_assets - cost_basis
        profit_pct = profit / cost_basis * 100 if cost_basis > 0 else 0
        
        return {
            'balance': self.balance,
            'initial_balance': self.initial_balance,
            'positions_value': positions_value,
            'total_assets': total_assets,
            'total_profit': profit,
            'total_profit_pct': profit_pct
        }
    
    def get_positions(self):
        """获取持仓"""
        positions_list = []
        for stock_code, pos in self.positions.items():
            current_price = self._get_current_price(stock_code)
            pos['current_price'] = current_price
            pos['current_value'] = current_price * pos['volume'] * 100
            pos['profit'] = (current_price - pos['avg_cost']) * pos['volume'] * 100
            pos['profit_pct'] = (current_price - pos['avg_cost']) / pos['avg_cost'] * 100 if pos['avg_cost'] > 0 else 0
            pos['stock_code'] = stock_code
            positions_list.append(pos)
        
        return positions_list
    
    def get_trade_history(self, start_date=None, end_date=None):
        """获取交易历史"""
        history = self.trade_history
        
        if start_date:
            history = [h for h in history if h['date'] >= start_date]
        if end_date:
            history = [h for h in history if h['date'] <= end_date]
        
        return sorted(history, key=lambda x: x['date'], reverse=True)
    
    def get_real_time_price(self, stock_code):
        """获取实时价格"""
        return {
            'stock_code': stock_code,
            'stock_name': self._get_stock_name(stock_code),
            'price': self._get_current_price(stock_code),
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def get_returns_data(self):
        """收益视图数据：账户汇总 + 资产曲线 + 各股已实现盈亏 + 最近交易（只读，不影响交易）"""
        from collections import defaultdict
        acc = self.get_account_balance()
        total_assets = acc['total_assets']
        initial = self.initial_balance

        sells = [t for t in self.trade_history if t.get('side') == 'SELL' and 'profit' in t]
        realized = sum(t['profit'] for t in sells)
        pos_cost = sum(p['avg_cost'] * p['volume'] * 100 for p in self.positions.values())
        unrealized = acc['positions_value'] - pos_cost

        today = datetime.now().strftime('%Y-%m-%d')
        today_realized = sum(t['profit'] for t in sells if t['date'][:10] == today)
        day_snaps = [s for s in self.returns_history if s['date'][:10] == today]
        if day_snaps:
            today_profit = total_assets - day_snaps[0]['total_assets']
        else:
            today_profit = today_realized

        wins = sum(1 for t in sells if t['profit'] > 0)
        sell_count = len(sells)
        win_rate = wins / sell_count * 100 if sell_count else None

        by_stock = defaultdict(lambda: {'name': '', 'realized': 0.0, 'trades': 0})
        for t in sells:
            b = by_stock[t['stock_code']]
            b['name'] = t.get('stock_name', '')
            b['realized'] += t['profit']
            b['trades'] += 1
        stock_perf = [
            {'code': c, 'name': v['name'], 'realized': round(v['realized'], 2), 'trades': v['trades']}
            for c, v in sorted(by_stock.items(), key=lambda x: x[1]['realized'], reverse=True)
        ]

        curve = [{'t': s['date'], 'v': s['total_assets']} for s in self.returns_history]
        if not curve:
            curve = [{'t': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'v': initial}]

        return {
            'ok': True,
            'initial_balance': initial,
            'total_assets': round(total_assets, 2),
            'balance': round(self.balance, 2),
            'positions_value': round(acc['positions_value'], 2),
            'total_profit': round(acc['total_profit'], 2),
            'total_profit_pct': round(acc['total_profit_pct'], 2),
            'realized': round(realized, 2),
            'unrealized': round(unrealized, 2),
            'today_profit': round(today_profit, 2),
            'trade_count': len(self.trade_history),
            'sell_count': sell_count,
            'win_rate': round(win_rate, 1) if win_rate is not None else None,
            'equity_curve': curve,
            'by_stock': stock_perf,
            'trades': self.get_trade_history()[:100],
        }
    
    def update_position_prices(self):
        """更新所有持仓价格"""
        for stock_code in list(self.positions.keys()):
            self.positions[stock_code]['current_price'] = self._get_current_price(stock_code)
        self._save_data()
    
    def reset_account(self):
        """重置账户"""
        self.balance = self.initial_balance
        self.positions = {}
        self.orders = {}
        self.trade_history = []
        self.returns_history = []
        self.__dict__.pop('_price_cache', None)
        self._save_data()
        print("[OK] 账户已重置")


class RealTradingAPI(TradingAPI):
    """真实交易API基类 - 需要对接券商接口"""
    
    def __init__(self):
        self.connected = False
        self.account_info = {}
        self.positions = {}
    
    def connect(self, api_key, secret_key, **kwargs):
        """连接交易API"""
        self.connected = True
        print("[OK] 模拟连接到真实交易API（演示模式）")
        return True
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
        print("[OK] 已断开交易API连接")
    
    def buy(self, stock_code, price, volume, order_type='MARKET'):
        """买入股票"""
        if not self.connected:
            print("[ERROR] 请先连接交易API")
            return None
        
        order_id = f"REAL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order = Order(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=self._get_stock_name(stock_code),
            side='BUY',
            order_type=order_type,
            price=price,
            volume=volume
        )
        
        # 演示模式：模拟提交订单
        order.submit()
        print(f"[OUT] 订单已提交（演示模式）: {order_id}")
        print(f"   {ORDER_SIDE['BUY']} {stock_code} {volume}手 @ {price:.2f}")
        
        return order
    
    def sell(self, stock_code, price, volume, order_type='MARKET'):
        """卖出股票"""
        if not self.connected:
            print("[ERROR] 请先连接交易API")
            return None
        
        order_id = f"REAL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order = Order(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=self._get_stock_name(stock_code),
            side='SELL',
            order_type=order_type,
            price=price,
            volume=volume
        )
        
        # 演示模式：模拟提交订单
        order.submit()
        print(f"[OUT] 订单已提交（演示模式）: {order_id}")
        print(f"   {ORDER_SIDE['SELL']} {stock_code} {volume}手 @ {price:.2f}")
        
        return order
    
    def cancel_order(self, order_id):
        """取消订单"""
        if not self.connected:
            print("[ERROR] 请先连接交易API")
            return False
        
        print(f"[OK] 订单取消请求已发送（演示模式）: {order_id}")
        return True
    
    def get_order_status(self, order_id):
        """获取订单状态"""
        if not self.connected:
            print("[ERROR] 请先连接交易API")
            return None
        
        # 演示模式：返回模拟状态
        order = Order(
            order_id=order_id,
            stock_code='000001',
            stock_name='测试股票',
            side='BUY',
            order_type='MARKET',
            price=10.0,
            volume=100
        )
        order.status = 'SUBMITTED'
        return order
    
    def get_open_orders(self):
        """获取所有未成交订单"""
        if not self.connected:
            print("[ERROR] 请先连接交易API")
            return []
        return []
    
    def get_account_balance(self):
        """获取账户资金"""
        if not self.connected:
            print("[ERROR] 请先连接交易API")
            return {}
        
        # 演示数据
        return {
            'balance': 50000.00,
            'initial_balance': 100000.00,
            'positions_value': 50000.00,
            'total_assets': 100000.00,
            'total_profit': 0.00,
            'total_profit_pct': 0.00
        }
    
    def get_positions(self):
        """获取持仓"""
        if not self.connected:
            print("[ERROR] 请先连接交易API")
            return []
        return []
    
    def get_trade_history(self, start_date=None, end_date=None):
        """获取交易历史"""
        if not self.connected:
            print("[ERROR] 请先连接交易API")
            return []
        return []
    
    def get_real_time_price(self, stock_code):
        """获取实时价格"""
        if not self.connected:
            print("[ERROR] 请先连接交易API")
            return {}
        
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == stock_code]
            if not stock_data.empty:
                return {
                    'stock_code': stock_code,
                    'stock_name': stock_data.iloc[0]['名称'],
                    'price': stock_data.iloc[0]['最新价'],
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        except Exception as e:
            print(f"[WARN] 获取实时价格失败: {e}")
        
        return {}
    
    def _get_stock_name(self, stock_code):
        """获取股票名称"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == stock_code]
            if not stock_data.empty:
                return stock_data.iloc[0]['名称']
        except:
            pass
        
        stock_names = {
            '000001': '平安银行',
            '000002': '万科A',
            '000333': '美的集团',
            '000651': '格力电器',
            '600000': '浦发银行',
            '600519': '贵州茅台',
            '601318': '中国平安',
            '600036': '招商银行',
            '000858': '五粮液',
            '002594': '比亚迪'
        }
        return stock_names.get(stock_code, f"股票{stock_code}")


class EasyTraderAPI(TradingAPI):
    """
    easytrader 适配器：通过操作本机券商客户端（同花顺/通达信/券商版）实现真实下单。
    依赖 easytrader + pywinauto，需要本机已安装并登录券商客户端。

    用法：
        api = EasyTraderAPI(broker='universal_client', exe_path='C:\\xxx\\xiadan.exe')
        api.connect(user='账号', password='密码')  # 或 api.prepare_config('config.json')
    """

    BROKER_ALIASES = {
        'universal': 'universal_client',   # 通用同花顺客户端
        'ths': 'ths',                      # 同花顺客户端
        'gj': 'gj_client',                 # 国金客户端
        'gf': 'gf_client',                 # 广发客户端
        'yh': 'yh_client',                 # 银河客户端
        'ht': 'ht_client',                 # 华泰客户端
        'htzq': 'htzq_client',             # 海通证券客户端
        'wk': 'wk_client',                 # 五矿客户端
        'xq': 'xq',                        # 雪球（网页）
    }

    def __init__(self, broker='universal_client', exe_path=None, **kwargs):
        self.broker = self.BROKER_ALIASES.get(str(broker).lower(), broker)
        self.exe_path = exe_path
        self._trader = None
        self.connected = False
        self.last_error = ''

    # ---------- 连接 ----------
    def connect(self, user=None, password=None, config_path=None, comm_password=None, **kwargs):
        """连接并登录券商客户端"""
        try:
            import easytrader
        except ImportError as e:
            self.last_error = f"未安装 easytrader: {e}。请先 pip install easytrader"
            raise RuntimeError(self.last_error)
        try:
            self._trader = easytrader.use(self.broker)
        except NotImplementedError:
            self.last_error = f"不支持的券商类型: {self.broker}"
            raise RuntimeError(self.last_error)

        try:
            if config_path:
                self._trader.prepare(config_path=config_path)
            else:
                # user/password 可留空：客户端已在本机运行并登录时仅附加连接；
                # 未运行时 easytrader 会用 user/password 尝试自动启动+登录。
                self._trader.prepare(user=user or None, password=password or None,
                                     exe_path=self.exe_path, comm_password=comm_password)
        except Exception as e:
            self.last_error = f"连接券商客户端失败: {e}"
            raise RuntimeError(self.last_error)
        self.connected = True
        return True

    def prepare_config(self, config_path):
        """通过配置文件连接（json: {'user','password','exe_path','comm_password'}）"""
        return self.connect(config_path=config_path)

    def disconnect(self):
        try:
            if self._trader:
                self._trader.exit()
        except Exception:
            pass
        self.connected = False

    def _require(self):
        if not self.connected or self._trader is None:
            raise RuntimeError("请先 connect() 连接券商客户端")

    # ---------- 下单 ----------
    def buy(self, stock_code, price, volume, order_type='LIMIT', **kwargs):
        """买入。volume 单位=手（与本系统其它API一致），内部×100转为股。"""
        self._require()
        shares = int(volume * 100)
        try:
            if order_type == 'MARKET':
                result = self._trader.market_buy(stock_code, shares)
            else:
                result = self._trader.buy(stock_code, float(price), shares)
            return self._wrap_order(result, stock_code, 'BUY', volume)
        except Exception as e:
            self.last_error = f"买入失败: {e}"
            raise RuntimeError(self.last_error)

    def sell(self, stock_code, price, volume, order_type='LIMIT', **kwargs):
        """卖出。volume 单位=手，内部×100转为股。"""
        self._require()
        shares = int(volume * 100)
        try:
            if order_type == 'MARKET':
                result = self._trader.market_sell(stock_code, shares)
            else:
                result = self._trader.sell(stock_code, float(price), shares)
            return self._wrap_order(result, stock_code, 'SELL', volume)
        except Exception as e:
            self.last_error = f"卖出失败: {e}"
            raise RuntimeError(self.last_error)

    def cancel_order(self, order_id, **kwargs):
        self._require()
        try:
            return self._trader.cancel_entrust(order_id)
        except Exception as e:
            self.last_error = f"撤单失败: {e}"
            raise RuntimeError(self.last_error)

    def cancel_all_orders(self):
        self._require()
        try:
            return self._trader.cancel_all_entrusts()
        except Exception as e:
            self.last_error = f"全部撤单失败: {e}"
            raise RuntimeError(self.last_error)

    # ---------- 查询 ----------
    def get_order_status(self, order_id):
        self._require()
        try:
            for t in self._trader.today_entrusts:
                if str(t.get('entrust_no', '')) == str(order_id):
                    return self._wrap_order(t, t.get('证券代码', ''), 'BUY')
            return None
        except Exception as e:
            self.last_error = f"查询订单状态失败: {e}"
            return None

    def get_open_orders(self):
        self._require()
        try:
            rows = self._trader.today_entrusts or []
            out = []
            for t in rows:
                if str(t.get('状态', '')).strip() not in ('已成', '已撤', '废单'):
                    out.append(self._wrap_order(t, t.get('证券代码', ''), 'BUY'))
            return out
        except Exception as e:
            self.last_error = f"查询未成交订单失败: {e}"
            return []

    def get_account_balance(self):
        self._require()
        try:
            b = self._trader.balance or {}
            total_assets = self._f(b.get('总资产', 0))
            balance = self._f(b.get('可用金额', 0))
            positions_value = self._f(b.get('总市值', 0)) if '总市值' in b else total_assets - balance
            return {
                'balance': balance,
                'initial_balance': self._f(b.get('期初资产', total_assets)),
                'positions_value': positions_value,
                'total_assets': total_assets,
                'total_profit': self._f(b.get('当日参考盈亏', 0)),
                'total_profit_pct': self._f(b.get('当日盈亏比例', 0)),
            }
        except Exception as e:
            self.last_error = f"获取账户资金失败: {e}"
            return {}

    def get_positions(self):
        self._require()
        try:
            rows = self._trader.position or []
            out = []
            for p in rows:
                code = str(p.get('证券代码', '')).zfill(6)
                if not code or code == '000000':
                    continue
                out.append({
                    'stock_code': code,
                    'name': p.get('证券名称', ''),
                    'volume': round(int(self._f(p.get('股票余额', p.get('当前持仓', 0)))) / 100.0, 2),
                    'avg_cost': self._f(p.get('参考成本价', p.get('成本价', 0))),
                    'current_price': self._f(p.get('市价', p.get('最新价', 0))),
                    'current_value': self._f(p.get('股票市值', 0)),
                    'profit': self._f(p.get('参考盈亏', 0)),
                    'profit_pct': self._f(p.get('盈亏比例(%)', 0)),
                })
            return out
        except Exception as e:
            self.last_error = f"获取持仓失败: {e}"
            return []

    def get_trade_history(self, start_date=None, end_date=None):
        self._require()
        try:
            rows = self._trader.today_trades or []
            out = []
            for t in rows:
                out.append({
                    'trade_id': t.get('成交编号', t.get('成交序号', '')),
                    'date': t.get('发生日期', t.get('成交时间', '')),
                    'stock_code': str(t.get('证券代码', '')).zfill(6),
                    'stock_name': t.get('证券名称', ''),
                    'side': 'BUY' if '买' in str(t.get('操作', t.get('买卖标志', ''))) else 'SELL',
                    'price': self._f(t.get('成交价格', 0)),
                    'volume': int(self._f(t.get('成交数量', 0))),
                    'amount': self._f(t.get('成交金额', 0)),
                })
            return out
        except Exception as e:
            self.last_error = f"获取交易历史失败: {e}"
            return []

    def get_real_time_price(self, stock_code):
        """真实价格由行情接口提供，这里返回模拟/缓存数据"""
        try:
            from 智能数据查询 import SmartDataClient
            df = SmartDataClient().get_realtime([stock_code])
            if df is not None and not df.empty:
                r = df.iloc[0]
                return {'stock_code': stock_code, 'stock_name': r.get('name', ''),
                        'price': self._f(r.get('price', 0)),
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        except Exception:
            pass
        return {'stock_code': stock_code, 'stock_name': '', 'price': 0.0,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    # ---------- 辅助 ----------
    @staticmethod
    def _f(v, default=0.0):
        try:
            v = float(v)
            return v
        except (TypeError, ValueError):
            return default

    def _wrap_order(self, result, stock_code, side, volume=None):
        """把 easytrader 返回的委托结果包装成 Order 对象"""
        if result is None:
            result = {}
        entrust_no = result.get('entrust_no') or result.get('委托编号') or \
            result.get('合同编号') or result.get('order_id') or 'N/A'
        order = Order(
            order_id=str(entrust_no),
            stock_code=stock_code,
            stock_name=result.get('证券名称', ''),
            side=side,
            order_type='LIMIT',
            price=self._f(result.get('委托价格', 0)),
            volume=volume if volume is not None else int(self._f(result.get('委托数量', result.get('委托量', 0)))) / 100.0,
        )
        order.status = 'SUBMITTED'
        msg = result.get('message') or result.get('message_no') or ''
        if '废单' in str(result.get('msg_type', '')) or '失败' in str(msg):
            order.reject(str(msg))
        return order


class TradingAPIFactory:
    """交易API工厂类"""
    
    @staticmethod
    def create_api(api_type='simulated', **kwargs):
        """
        创建交易API实例
        :param api_type: 'simulated' / 'real' / 'easytrader'
        :param kwargs: 额外参数
        :return: TradingAPI实例
        """
        if api_type.lower() == 'simulated':
            initial_balance = kwargs.get('initial_balance', 100000.0)
            data_source = kwargs.get('data_source')
            return SimulatedTradingAPI(initial_balance, data_source)
        elif api_type.lower() == 'real':
            return RealTradingAPI()
        elif api_type.lower() == 'easytrader':
            return EasyTraderAPI(**kwargs)
        else:
            raise ValueError(f"未知的API类型: {api_type}")


# 示例用法
if __name__ == '__main__':
    print("=" * 60)
    print("股票交易API测试")
    print("=" * 60)
    
    # 创建模拟交易API
    api = TradingAPIFactory.create_api('simulated', initial_balance=100000)
    
    print("\n1. 获取账户信息")
    balance = api.get_account_balance()
    print(f"   总资产: {balance['total_assets']:.2f}")
    print(f"   可用余额: {balance['balance']:.2f}")
    
    print("\n2. 测试买入")
    order = api.buy('600519', 0, 1, order_type='MARKET')  # 市价买入1手茅台
    if order:
        print(f"   订单ID: {order.order_id}")
        print(f"   状态: {ORDER_STATUS.get(order.status, order.status)}")
    
    print("\n3. 获取持仓")
    positions = api.get_positions()
    for pos in positions:
        print(f"   {pos['stock_code']} {pos['name']}: {pos['volume']}手")
    
    print("\n4. 测试卖出")
    order = api.sell('600519', 0, 1, order_type='MARKET')  # 市价卖出1手茅台
    if order:
        print(f"   订单ID: {order.order_id}")
        print(f"   状态: {ORDER_STATUS.get(order.status, order.status)}")
    
    print("\n5. 最终账户信息")
    balance = api.get_account_balance()
    print(f"   总资产: {balance['total_assets']:.2f}")
    print(f"   总收益: {balance['total_profit']:+.2f} ({balance['total_profit_pct']:+.2f}%)")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)