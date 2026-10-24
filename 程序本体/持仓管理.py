"""
持仓管理模块
用于管理和跟踪用户的股票持仓信息
"""

import os
import json
import pickle
from datetime import datetime
import pandas as pd


class Position:
    """持仓信息类"""
    
    def __init__(self, stock_code, stock_name, volume, avg_price, buy_date):
        self.stock_code = stock_code          # 股票代码
        self.stock_name = stock_name          # 股票名称
        self.volume = volume                  # 持仓数量(股)
        self.avg_price = avg_price            # 平均成本价
        self.buy_date = buy_date              # 买入日期
        self.current_price = avg_price        # 当前价格
        self.total_cost = avg_price * volume  # 总成本
        self.current_value = self.total_cost  # 当前市值
    
    def update_price(self, current_price):
        """更新当前价格"""
        self.current_price = current_price
        self.current_value = current_price * self.volume
    
    def get_profit_loss(self):
        """计算盈亏"""
        return self.current_value - self.total_cost
    
    def get_profit_loss_pct(self):
        """计算盈亏百分比"""
        if self.total_cost > 0:
            return (self.current_value - self.total_cost) / self.total_cost * 100
        return 0
    
    def to_dict(self):
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'volume': self.volume,
            'avg_price': self.avg_price,
            'buy_date': str(self.buy_date),
            'current_price': self.current_price,
            'total_cost': self.total_cost,
            'current_value': self.current_value
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建对象"""
        # 尝试多种日期格式
        date_str = data['buy_date']
        try:
            # 尝试带时间的格式: 2025-01-15 15:13:12
            buy_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # 尝试带微秒的格式: 2025-01-15 15:13:12.197839
                buy_date = datetime.strptime(date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # 尝试简单日期格式: 2025-01-15
                    buy_date = datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    # 都失败了,使用当前日期
                    buy_date = datetime.now()

        return cls(
            stock_code=data['stock_code'],
            stock_name=data['stock_name'],
            volume=data['volume'],
            avg_price=data['avg_price'],
            buy_date=buy_date
        )


class PortfolioManager:
    """投资组合管理器"""
    
    def __init__(self, file_path='portfolio.pkl'):
        self.file_path = file_path
        self.positions = {}           # 股票代码 -> Position对象
        self.cash = 100000.0          # 可用资金
        self.initial_cash = 100000.0  # 初始资金
        self.history = []             # 交易历史
        self.load_portfolio()
    
    def add_position(self, stock_code, stock_name, volume, price, date=None):
        """添加持仓(买入) volume 单位为股"""
        if date is None:
            date = datetime.now()
        
        cost = price * volume
        
        if cost > self.cash:
            print(f"[ERROR] Insufficient funds: Need {cost:.2f}, Available {self.cash:.2f}")
            return False
        
        # 如果已有该股票,更新持仓
        if stock_code in self.positions:
            old_pos = self.positions[stock_code]
            old_volume = old_pos.volume
            old_cost = old_pos.total_cost
            
            # 计算新的平均成本
            new_volume = old_volume + volume
            new_avg_price = (old_cost + cost) / new_volume
            
            old_pos.volume = new_volume
            old_pos.avg_price = new_avg_price
            old_pos.total_cost = old_cost + cost
            old_pos.current_value = old_pos.total_cost
        else:
            # 新建持仓
            self.positions[stock_code] = Position(
                stock_code=stock_code,
                stock_name=stock_name,
                volume=volume,
                avg_price=price,
                buy_date=date
            )
            self.positions[stock_code].total_cost = cost
            self.positions[stock_code].current_value = cost
        
        # 扣除资金
        self.cash -= cost
        
        # 记录交易历史
        self.history.append({
            'date': str(date) if isinstance(date, datetime) else date,
            'action': 'buy',
            'stock_code': stock_code,
            'stock_name': stock_name,
            'price': price,
            'volume': volume,
            'amount': cost
        })
        
        print(f"[OK] Buy success: {stock_name}({stock_code}) {volume} shares @ {price:.2f}")
        print(f"   Cost: {cost:.2f}, Remaining: {self.cash:.2f}")
        
        self.save_portfolio()
        return True
    
    def reduce_position(self, stock_code, volume, price, date=None):
        """减少持仓(卖出) volume 单位为股"""
        if date is None:
            date = datetime.now()
        
        if stock_code not in self.positions:
            print(f"[ERROR] No position for stock: {stock_code}")
            return False
        
        pos = self.positions[stock_code]
        
        if volume > pos.volume:
            print(f"[ERROR] Insufficient position: Want to sell {volume}, only have {pos.volume}")
            return False
        
        # 计算收益
        revenue = price * volume
        cost_price = pos.avg_price
        cost = cost_price * volume
        profit = revenue - cost
        profit_pct = profit / cost * 100 if cost > 0 else 0
        
        # 更新持仓
        pos.volume -= volume
        pos.total_cost -= cost
        
        # 如果全部卖出,删除持仓
        if pos.volume == 0:
            del self.positions[stock_code]
        else:
            # 更新当前市值
            pos.current_value = pos.avg_price * pos.volume
        
        # 增加资金
        self.cash += revenue
        
        # 记录交易历史
        self.history.append({
            'date': str(date) if isinstance(date, datetime) else date,
            'action': 'sell',
            'stock_code': stock_code,
            'stock_name': pos.stock_name if stock_code in self.positions else self._get_stock_name_from_history(stock_code),
            'price': price,
            'volume': volume,
            'amount': revenue,
            'profit': profit,
            'profit_pct': profit_pct
        })
        
        print("[OK] Sell success: %s(%s) %d lots @ %.2f" % ((pos.stock_name if stock_code in self.positions else stock_code), stock_code, volume, price))
        print(f"   Revenue: {revenue:.2f}, P&L: {profit:+.2f} ({profit_pct:+.2f}%)")
        print(f"   Remaining: {self.cash:.2f}")
        
        self.save_portfolio()
        return True
    
    def _get_stock_name_from_history(self, stock_code):
        """从交易历史中查找股票名称"""
        for record in reversed(self.history):
            if record['stock_code'] == stock_code:
                return record['stock_name']
        return stock_code
    
    def update_all_prices(self, price_dict):
        """更新所有持仓的当前价格
        price_dict: {股票代码: 当前价格}
        """
        updated = False
        for stock_code, price in price_dict.items():
            if stock_code in self.positions:
                self.positions[stock_code].update_price(price)
                updated = True
        
        if updated:
            self.save_portfolio()
        
        return updated
    
    def get_total_value(self):
        """获取总资产"""
        total_value = self.cash
        for pos in self.positions.values():
            total_value += pos.current_value
        return total_value
    
    def get_total_cost(self):
        """获取总成本"""
        total_cost = self.cash
        for pos in self.positions.values():
            total_cost += pos.total_cost
        return total_cost
    
    def get_total_profit_loss(self):
        """获取总盈亏"""
        return self.get_total_value() - self.get_total_cost()
    
    def get_total_profit_loss_pct(self):
        """获取总盈亏百分比"""
        total_cost = self.get_total_cost()
        if total_cost > 0:
            return self.get_total_profit_loss() / total_cost * 100
        return 0
    
    def get_position_list(self):
        """获取持仓列表"""
        return list(self.positions.values())
    
    def get_position(self, stock_code):
        """获取指定股票的持仓"""
        return self.positions.get(stock_code, None)
    
    def has_position(self, stock_code):
        """检查是否有某股票的持仓"""
        return stock_code in self.positions
    
    def display_portfolio(self):
        """显示投资组合"""
        print("\n" + "="*80)
        print("[PORTFOLIO] Investment Portfolio Overview")
        print("="*80)

        print(f"\n[CASH] Fund Information:")
        print(f"   Available: {self.cash:,.2f}")
        print(f"   Initial: {self.initial_cash:,.2f}")

        if self.positions:
            print(f"\n[POSITIONS] Position Details ({len(self.positions)} stocks):")
            print("-"*80)
            print(f"{'股票代码':<10} {'股票名称':<12} {'数量(股)':<10} {'成本价':<10} {'现价':<10} {'市值':<12} {'盈亏':<12} {'盈亏%':<10}")
            print("-"*80)
            
            total_cost = 0
            total_value = 0
            
            for pos in sorted(self.positions.values(), key=lambda x: x.current_value, reverse=True):
                profit = pos.get_profit_loss()
                profit_pct = pos.get_profit_loss_pct()
                
                # 盈亏颜色标记
                profit_str = f"{profit:+,.2f}"
                profit_pct_str = f"{profit_pct:+.2f}%"
                
                print(f"{pos.stock_code:<10} {pos.stock_name:<12} {pos.volume:<10} "
                      f"{pos.avg_price:<10.2f} {pos.current_price:<10.2f} "
                      f"{pos.current_value:<12,.2f} {profit_str:<12} {profit_pct_str:<10}")
                
                total_cost += pos.total_cost
                total_value += pos.current_value
            
            print("-"*80)
            print(f"{'合计':<10} {'':<12} {'':<10} {'':<10} {'':<10} "
                  f"{total_value:<12,.2f} {total_value-total_cost:<12,.2f} {(total_value-total_cost)/total_cost*100 if total_cost>0 else 0:<+9.2f}%")
        
        # 总资产
        total_asset = self.get_total_value()
        total_profit = total_asset - self.initial_cash
        total_profit_pct = total_profit / self.initial_cash * 100

        print("\n" + "="*80)
        print(f"[TOTAL] Total Asset: {total_asset:,.2f}")
        print(f"[P&L] Total Profit: {total_profit:+,.2f} ({total_profit_pct:+.2f}%)")
        print("="*80 + "\n")
        
        return {
            'cash': self.cash,
            'positions_count': len(self.positions),
            'total_value': total_asset,
            'total_profit': total_profit,
            'total_profit_pct': total_profit_pct
        }
    
    def display_history(self, limit=20):
        """显示交易历史"""
        print("\n" + "="*80)
        print(f"[HISTORY] Recent {limit} Transactions")
        print("="*80)

        recent_history = self.history[-limit:]

        if not recent_history:
            print("  No transactions")
        else:
            print("-"*80)
            print(f"{'Date':<12} {'Action':<6} {'Stock':<16} {'Price':<10} {'Volume':<10} {'Amount':<12} {'P&L':<12}")
            print("-"*80)

            for record in reversed(recent_history):
                action = record['action']
                action_str = "BUY" if action == 'buy' else "SELL"

                stock_name = f"{record['stock_name']}({record['stock_code']})"

                profit_str = ""
                if action == 'sell':
                    profit_str = f"{record['profit']:+,.2f}"

                print(f"{record['date'][:10]:<12} {action_str:<6} {stock_name:<16} "
                      f"{record['price']:<10.2f} {record['volume']:<10} "
                      f"{record['amount']:<12,.2f} {profit_str:<12}")

        print("="*80 + "\n")
    
    def get_ai_trading_signal(self, stock_code, ai_prediction, current_price):
        """
        根据AI预测和持仓情况生成交易建议
        
        参数:
            stock_code: 股票代码
            ai_prediction: AI预测 (1=看涨, -1=看跌, 0=中性)
            current_price: 当前价格
        
        返回:
            信号: 'BUY', 'SELL', 'HOLD'
            理由: 信号说明
        """
        has_position = self.has_position(stock_code)
        
        # 没有持仓的情况
        if not has_position:
            if ai_prediction == 1:
                # AI看涨,且没有持仓,建议买入
                return 'BUY', f"AI预测看涨,建议买入建仓"
            else:
                return 'HOLD', f"未持仓,AI预测{'看跌' if ai_prediction == -1 else '中性'},建议观望"
        
        # 有持仓的情况
        position = self.get_position(stock_code)
        profit_pct = position.get_profit_loss_pct()
        
        if ai_prediction == 1:
            # AI看涨
            if profit_pct < -5:
                return 'BUY', f"AI看涨,当前亏损{profit_pct:.2f}%,可考虑加仓摊低成本"
            elif profit_pct < 5:
                return 'HOLD', f"AI看涨,持仓盈利{profit_pct:.2f}%,建议继续持有"
            else:
                # 盈利较多,考虑止盈
                return 'HOLD', f"AI看涨但已盈利{profit_pct:.2f}%,可考虑分批止盈"
        
        elif ai_prediction == -1:
            # AI看跌
            if profit_pct > 5:
                return 'SELL', f"AI看跌,当前盈利{profit_pct:.2f}%,建议及时止盈"
            elif profit_pct > 0:
                return 'SELL', f"AI看跌,小幅盈利{profit_pct:.2f}%,建议减仓或清仓"
            else:
                return 'SELL', f"AI看跌,当前亏损{profit_pct:.2f}%,建议止损"
        
        else:
            # AI中性
            if profit_pct > 10:
                return 'SELL', f"AI中性但盈利{profit_pct:.2f}%,建议止盈"
            elif profit_pct < -10:
                return 'SELL', f"AI中性且亏损{profit_pct:.2f}%,建议止损"
            else:
                return 'HOLD', f"AI中性,波动在合理范围,建议继续持有"
    
    def update_position(self, stock_code, stock_name, volume, avg_price, buy_date=None):
        """直接设置/修改某只股票的持仓（数量单位：股）
        如果 volume <= 0 则删除该持仓
        """
        if volume <= 0:
            return self.remove_position(stock_code)

        if buy_date is None:
            buy_date = datetime.now()

        pos = self.positions.get(stock_code)
        if pos is None:
            pos = Position(stock_code, stock_name, volume, avg_price, buy_date)
        else:
            pos.stock_name = stock_name or pos.stock_name
            pos.volume = volume
            pos.avg_price = avg_price
        pos.total_cost = avg_price * volume
        pos.current_value = pos.total_cost
        pos.current_price = avg_price
        self.positions[stock_code] = pos
        self.save_portfolio()
        return True

    def remove_position(self, stock_code):
        """删除某只股票的持仓"""
        if stock_code in self.positions:
            del self.positions[stock_code]
            self.save_portfolio()
            return True
        return False

    def set_cash(self, amount):
        """直接设置可用现金（单位：元）"""
        self.cash = float(amount)
        self.save_portfolio()
        return True

    def replace_all_positions(self, items, cash=None):
        """用导入的持仓明细整体替换当前持仓
        items: [{code, name, volume, avg_price}]  volume 单位为股
        cash: 可选，若给到则一并更新可用资金
        """
        new_positions = {}
        for it in items:
            code = str(it.get('code', '')).strip()
            vol = float(it.get('volume', 0) or 0)
            avg = float(it.get('avg_price', 0) or 0)
            if not code or vol <= 0:
                continue
            pos = Position(
                stock_code=code,
                stock_name=str(it.get('name', '') or code),
                volume=vol,
                avg_price=avg,
                buy_date=datetime.now()
            )
            pos.total_cost = avg * vol
            pos.current_value = pos.total_cost
            new_positions[code] = pos

        self.positions = new_positions
        if cash is not None:
            self.cash = float(cash)
        self.save_portfolio()
        return len(new_positions)

    def apply_transactions(self, records, initial_cash=None):
        """用交割单（买卖流水）重建持仓
        records: [{date, code, name, action(buy/sell), price, volume, amount}]
        initial_cash: 可选，从该资金开始逐笔结算
        返回 (持仓数, 成交笔数)
        """
        if initial_cash is not None:
            self.cash = float(initial_cash)

        # 先清空现有持仓（避免和流水叠加）
        self.positions.clear()

        applied = 0
        for r in sorted(records, key=lambda x: str(x.get('date', ''))):
            code = str(r.get('code', '')).strip()
            name = str(r.get('name', '') or code)
            price = float(r.get('price', 0) or 0)
            volume = float(r.get('volume', 0) or 0)
            action = r.get('action', 'buy')
            if not code or volume <= 0:
                continue

            if action == 'sell':
                pos = self.positions.get(code)
                if pos is None:
                    continue
                qty = min(volume, pos.volume)
                revenue = price * qty
                cost = pos.avg_price * qty
                pos.volume -= qty
                pos.total_cost -= cost
                if pos.volume <= 0:
                    del self.positions[code]
                self.cash += revenue
            else:
                cost = price * volume
                if self.cash < cost:
                    continue
                pos = self.positions.get(code)
                if pos is None:
                    pos = Position(code, name, volume, price, datetime.now())
                    pos.total_cost = cost
                    pos.current_value = cost
                    self.positions[code] = pos
                else:
                    old_vol = pos.volume
                    old_cost = pos.total_cost
                    new_vol = old_vol + volume
                    pos.volume = new_vol
                    pos.avg_price = (old_cost + cost) / new_vol
                    pos.total_cost = old_cost + cost
                    pos.current_value = pos.total_cost
                self.cash -= cost
            applied += 1

        self.save_portfolio()
        return len(self.positions), applied

    def save_portfolio(self):
        """保存投资组合到文件"""
        try:
            data = {
                'cash': self.cash,
                'initial_cash': self.initial_cash,
                'positions': {k: v.to_dict() for k, v in self.positions.items()},
                'history': self.history
            }
            
            with open(self.file_path, 'wb') as f:
                pickle.dump(data, f)
            
            # 同时保存JSON格式便于查看
            json_path = self.file_path.replace('.pkl', '.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save portfolio: {e}")
            return False
    
    def load_portfolio(self):
        """从文件加载投资组合"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'rb') as f:
                    data = pickle.load(f)
                
                self.cash = data.get('cash', 100000.0)
                self.initial_cash = data.get('initial_cash', 100000.0)
                self.history = data.get('history', [])
                
                # 恢复持仓
                positions_dict = data.get('positions', {})
                for stock_code, pos_data in positions_dict.items():
                    pos = Position.from_dict(pos_data)
                    self.positions[stock_code] = pos
                
                print(f"[OK] Portfolio loaded: {len(self.positions)} positions, cash {self.cash:,.2f}")
                return True
        except Exception as e:
            print(f"[WARNING] Failed to load portfolio: {e} (creating new portfolio)")
        
        return False
    
    def clear_portfolio(self):
        """清空投资组合"""
        self.positions.clear()
        self.cash = self.initial_cash
        self.history.clear()
        self.save_portfolio()
        print("[OK] Portfolio cleared")


# 便捷函数
def get_portfolio_manager(file_path='portfolio.pkl'):
    """获取投资组合管理器实例"""
    return PortfolioManager(file_path)


# ==================== 基金管理类 ====================

class FundPosition:
    """基金持仓信息类"""

    def __init__(self, fund_code, fund_name, volume, avg_nav, buy_date, fund_type="混合型"):
        self.fund_code = fund_code          # 基金代码
        self.fund_name = fund_name          # 基金名称
        self.fund_type = fund_type          # 基金类型
        self.volume = volume                # 持仓份额
        self.avg_nav = avg_nav              # 平均成本净值
        self.buy_date = buy_date            # 买入日期
        self.current_nav = avg_nav          # 当前净值
        self.total_cost = avg_nav * volume  # 总成本
        self.current_value = self.total_cost  # 当前市值

    def update_nav(self, current_nav):
        """更新当前净值"""
        self.current_nav = current_nav
        self.current_value = current_nav * self.volume

    def get_profit_loss(self):
        """计算盈亏"""
        return self.current_value - self.total_cost

    def get_profit_loss_pct(self):
        """计算盈亏百分比"""
        if self.total_cost > 0:
            return (self.current_value - self.total_cost) / self.total_cost * 100
        return 0

    def to_dict(self):
        """转换为字典"""
        return {
            'fund_code': self.fund_code,
            'fund_name': self.fund_name,
            'fund_type': self.fund_type,
            'volume': self.volume,
            'avg_nav': self.avg_nav,
            'buy_date': str(self.buy_date),
            'current_nav': self.current_nav,
            'total_cost': self.total_cost,
            'current_value': self.current_value
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建对象"""
        # 尝试多种日期格式
        date_str = data['buy_date']
        try:
            buy_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                buy_date = datetime.strptime(date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    buy_date = datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    buy_date = datetime.now()

        return cls(
            fund_code=data['fund_code'],
            fund_name=data['fund_name'],
            volume=data['volume'],
            avg_nav=data['avg_nav'],
            buy_date=buy_date,
            fund_type=data.get('fund_type', '混合型')
        )


class FundManager:
    """基金投资组合管理器"""

    def __init__(self, file_path='fund_portfolio.pkl'):
        self.file_path = file_path
        self.funds = {}                    # 基金代码 -> FundPosition对象
        self.cash = 0.0                    # 可用资金
        self.initial_cash = 0.0            # 初始资金
        self.history = []                  # 交易历史
        self.load_portfolio()

    def add_position(self, fund_code, fund_name, volume, nav, date=None):
        """添加基金持仓(买入)"""
        if date is None:
            date = datetime.now()

        cost = nav * volume

        # 如果已有该基金,更新持仓
        if fund_code in self.funds:
            old_pos = self.funds[fund_code]
            old_volume = old_pos.volume
            old_cost = old_pos.total_cost

            # 计算新的平均成本
            new_volume = old_volume + volume
            new_avg_nav = (old_cost + cost) / new_volume

            old_pos.volume = new_volume
            old_pos.avg_nav = new_avg_nav
            old_pos.total_cost = old_cost + cost
            old_pos.current_value = old_pos.total_cost
        else:
            # 新建持仓
            self.funds[fund_code] = FundPosition(
                fund_code=fund_code,
                fund_name=fund_name,
                volume=volume,
                avg_nav=nav,
                buy_date=date
            )
            self.funds[fund_code].total_cost = cost
            self.funds[fund_code].current_value = cost

        # 记录交易历史
        self.history.append({
            'date': str(date) if isinstance(date, datetime) else date,
            'action': 'buy',
            'fund_code': fund_code,
            'fund_name': fund_name,
            'nav': nav,
            'volume': volume,
            'amount': cost
        })

        print(f"[OK] Buy fund success: {fund_name}({fund_code}) {volume:.2f} shares @ {nav:.4f}")
        print(f"   Cost: {cost:.2f}")

        self.save_portfolio()
        return True

    def reduce_position(self, fund_code, volume, nav, date=None):
        """减少基金持仓(卖出)"""
        if date is None:
            date = datetime.now()

        if fund_code not in self.funds:
            print(f"[ERROR] No position for fund: {fund_code}")
            return False

        pos = self.funds[fund_code]

        if volume > pos.volume:
            print(f"[ERROR] Insufficient position: Want to sell {volume}, only have {pos.volume}")
            return False

        # 计算收益
        revenue = nav * volume
        cost_nav = pos.avg_nav
        cost = cost_nav * volume
        profit = revenue - cost
        profit_pct = profit / cost * 100 if cost > 0 else 0

        # 更新持仓
        pos.volume -= volume
        pos.total_cost -= cost

        # 如果全部卖出,删除持仓
        if pos.volume == 0:
            del self.funds[fund_code]
        else:
            # 更新当前市值
            pos.current_value = pos.avg_nav * pos.volume

        # 记录交易历史
        self.history.append({
            'date': str(date) if isinstance(date, datetime) else date,
            'action': 'sell',
            'fund_code': fund_code,
            'fund_name': pos.fund_name if fund_code in self.funds else self._get_fund_name_from_history(fund_code),
            'nav': nav,
            'volume': volume,
            'amount': revenue,
            'profit': profit,
            'profit_pct': profit_pct
        })

        print(f"[OK] Sell fund success: {pos.fund_name if fund_code in self.funds else fund_code}({fund_code}) {volume:.2f} shares @ {nav:.4f}")
        print(f"   Revenue: {revenue:.2f}, P&L: {profit:+,.2f} ({profit_pct:+.2f}%)")

        self.save_portfolio()
        return True

    def _get_fund_name_from_history(self, fund_code):
        """从交易历史中查找基金名称"""
        for record in reversed(self.history):
            if record['fund_code'] == fund_code:
                return record['fund_name']
        return fund_code

    def update_all_nav(self, nav_dict):
        """更新所有持仓的当前净值
        nav_dict: {基金代码: 当前净值}
        """
        updated = False
        for fund_code, nav in nav_dict.items():
            if fund_code in self.funds:
                self.funds[fund_code].update_nav(nav)
                updated = True

        if updated:
            self.save_portfolio()

        return updated

    def get_total_value(self):
        """获取总资产"""
        total_value = self.cash
        for pos in self.funds.values():
            total_value += pos.current_value
        return total_value

    def get_total_cost(self):
        """获取总成本"""
        total_cost = self.cash
        for pos in self.funds.values():
            total_cost += pos.total_cost
        return total_cost

    def get_total_profit_loss(self):
        """获取总盈亏"""
        return self.get_total_value() - self.get_total_cost()

    def get_total_profit_loss_pct(self):
        """获取总盈亏百分比"""
        total_cost = self.get_total_cost()
        if total_cost > 0:
            return self.get_total_profit_loss() / total_cost * 100
        return 0

    def get_position_list(self):
        """获取持仓列表"""
        return list(self.funds.values())

    def get_position(self, fund_code):
        """获取指定基金的持仓"""
        return self.funds.get(fund_code, None)

    def has_position(self, fund_code):
        """检查是否有某基金的持仓"""
        return fund_code in self.funds

    def display_portfolio(self):
        """显示基金投资组合"""
        print("\n" + "="*80)
        print("[FUND PORTFOLIO] Fund Investment Portfolio Overview")
        print("="*80)

        print(f"\n[CASH] Fund Information:")
        print(f"   Available: {self.cash:,.2f}")
        print(f"   Initial: {self.initial_cash:,.2f}")

        if self.funds:
            print(f"\n[FUNDS] Position Details ({len(self.funds)} funds):")
            print("-"*80)
            print(f"{'基金代码':<10} {'基金名称':<20} {'基金类型':<10} {'份额':<12} {'成本净值':<10} {'最新净值':<10} {'市值':<12} {'盈亏':<12} {'盈亏%':<10}")
            print("-"*80)

            total_cost = 0
            total_value = 0

            for pos in sorted(self.funds.values(), key=lambda x: x.current_value, reverse=True):
                profit = pos.get_profit_loss()
                profit_pct = pos.get_profit_loss_pct()

                profit_str = f"{profit:+,.2f}"
                profit_pct_str = f"{profit_pct:+.2f}%"

                print(f"{pos.fund_code:<10} {pos.fund_name:<20} {pos.fund_type:<10} "
                      f"{pos.volume:<12.2f} {pos.avg_nav:<10.4f} {pos.current_nav:<10.4f} "
                      f"{pos.current_value:<12,.2f} {profit_str:<12} {profit_pct_str:<10}")

                total_cost += pos.total_cost
                total_value += pos.current_value

            print("-"*80)
            print(f"{'合计':<10} {'':<20} {'':<10} {'':<12} {'':<10} {'':<10} "
                  f"{total_value:<12,.2f} {total_value-total_cost:<12,.2f} {(total_value-total_cost)/total_cost*100 if total_cost>0 else 0:<+9.2f}%")

        # 总资产
        total_asset = self.get_total_value()
        total_profit = total_asset - self.initial_cash
        total_profit_pct = total_profit / self.initial_cash * 100 if self.initial_cash > 0 else 0

        print("\n" + "="*80)
        print(f"[TOTAL] Total Asset: {total_asset:,.2f}")
        print(f"[P&L] Total Profit: {total_profit:+,.2f} ({total_profit_pct:+.2f}%)")
        print("="*80 + "\n")

        return {
            'cash': self.cash,
            'funds_count': len(self.funds),
            'total_value': total_asset,
            'total_profit': total_profit,
            'total_profit_pct': total_profit_pct
        }

    def save_portfolio(self):
        """保存基金投资组合到文件"""
        try:
            data = {
                'cash': self.cash,
                'initial_cash': self.initial_cash,
                'funds': {k: v.to_dict() for k, v in self.funds.items()},
                'history': self.history
            }

            with open(self.file_path, 'wb') as f:
                pickle.dump(data, f)

            # 同时保存JSON格式便于查看
            json_path = self.file_path.replace('.pkl', '.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"[ERROR] Failed to save fund portfolio: {e}")
            return False

    def load_portfolio(self):
        """从文件加载基金投资组合"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'rb') as f:
                    data = pickle.load(f)

                self.cash = data.get('cash', 0.0)
                self.initial_cash = data.get('initial_cash', 0.0)
                self.history = data.get('history', [])

                # 恢复持仓
                funds_dict = data.get('funds', {})
                for fund_code, fund_data in funds_dict.items():
                    fund_pos = FundPosition.from_dict(fund_data)
                    self.funds[fund_code] = fund_pos

                print(f"[OK] Fund portfolio loaded: {len(self.funds)} funds, cash {self.cash:,.2f}")
                return True
        except Exception as e:
            print(f"[WARNING] Failed to load fund portfolio: {e} (creating new portfolio)")

        return False

    def clear_portfolio(self):
        """清空基金投资组合"""
        self.funds.clear()
        self.cash = self.initial_cash
        self.history.clear()
        self.save_portfolio()
        print("[OK] Fund portfolio cleared")


if __name__ == "__main__":
    """测试代码"""
    pm = PortfolioManager('test_portfolio.pkl')
    
    # 添加一些测试持仓
    print("\n测试添加持仓:")
    pm.add_position('000001', '平安银行', 100, 10.50)
    pm.add_position('000002', '万科A', 200, 15.80)
    
    # 显示组合
    pm.display_portfolio()
    
    # 更新价格
    print("\n更新价格:")
    pm.update_all_prices({
        '000001': 11.20,
        '000002': 14.50
    })
    
    # 再次显示
    pm.display_portfolio()
    
    # 测试AI交易信号
    print("\nAI交易信号测试:")
    for stock_code, price in [('000001', 11.20), ('000002', 14.50), ('600000', 6.50)]:
        for ai_pred in [1, 0, -1]:
            signal, reason = pm.get_ai_trading_signal(stock_code, ai_pred, price)
            print(f"{stock_code} AI={ai_pred}: {signal} - {reason}")
    
    # 显示交易历史
    pm.display_history()
