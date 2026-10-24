"""
全自动交易策略执行引擎
负责连接AI策略、监控市场、执行交易、风险控制
"""

import time
import threading
import json
import os
from datetime import datetime, time as dt_time, timedelta
from queue import Queue
import pandas as pd

# 交易时段配置
TRADING_HOURS = {
    'morning_start': dt_time(9, 30),
    'morning_end': dt_time(11, 30),
    'afternoon_start': dt_time(13, 0),
    'afternoon_end': dt_time(15, 0)
}

# 交易信号类型
SIGNAL_TYPE = {
    'BUY': '买入信号',
    'SELL': '卖出信号',
    'HOLD': '持有信号',
    'NONE': '无信号'
}

# 风险控制配置
RISK_CONFIG = {
    'max_single_position_ratio': 0.3,  # 单只股票最大持仓比例
    'max_total_position_ratio': 0.8,   # 总持仓最大比例
    'min_balance_ratio': 0.2,          # 最小可用余额比例
    'stop_loss_pct': 0.05,             # 止损比例
    'take_profit_pct': 0.10,           # 止盈比例
    'max_daily_trades': 999999         # 每日最大交易次数（默认不限量）
}


class TradingSignal:
    """交易信号类"""
    
    def __init__(self, stock_code, signal_type, confidence=0.5, price=None, reason=''):
        self.stock_code = stock_code
        self.signal_type = signal_type  # BUY, SELL, HOLD, NONE
        self.confidence = confidence    # 置信度 0-1
        self.price = price              # 建议价格
        self.reason = reason            # 信号原因
        self.timestamp = datetime.now()
    
    def to_dict(self):
        return {
            'stock_code': self.stock_code,
            'signal_type': self.signal_type,
            'signal_text': SIGNAL_TYPE.get(self.signal_type, self.signal_type),
            'confidence': f"{self.confidence:.2%}",
            'price': self.price,
            'reason': self.reason,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }


class AutoTradingEngine:
    """全自动交易引擎"""
    
    def __init__(self, trading_api, ai_strategy, data_source=None, allow_off_hours=False):
        """
        初始化交易引擎
        :param trading_api: 交易API实例
        :param ai_strategy: AI策略实例
        :param data_source: 数据源实例
        :param allow_off_hours: 是否允许非交易时段也执行（模拟盘练习用）
        """
        self.trading_api = trading_api
        self.ai_strategy = ai_strategy
        self.data_source = data_source
        self.allow_off_hours = allow_off_hours
        
        # 运行状态
        self.running = False
        self.paused = False
        self.trading_enabled = True
        
        # 交易统计
        self.daily_trades = 0
        self.today_date = datetime.now().date()
        
        # 信号队列
        self.signal_queue = Queue(maxsize=100)
        
        # 交易日志
        self.trade_logs = []
        
        # 持仓跟踪
        self.last_positions = {}
        
        # 线程
        self.monitor_thread = None
        self.signal_thread = None
        self.executor_thread = None
        
        # 风险控制
        self.risk_config = RISK_CONFIG.copy()
        
        # 初始化日志文件
        self._init_log_file()
    
    def _init_log_file(self):
        """初始化日志文件"""
        log_dir = 'trading_logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.log_file_path = os.path.join(log_dir, f"trading_log_{datetime.now().strftime('%Y%m%d')}.log")
    
    def _log(self, message, level='INFO'):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        print(log_entry)
        
        # 写入日志文件
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"[WARN] 写入日志失败: {e}")
        
        # 保存到内存
        self.trade_logs.append({
            'timestamp': timestamp,
            'level': level,
            'message': message
        })
        
        # 保留最近1000条日志
        if len(self.trade_logs) > 1000:
            self.trade_logs = self.trade_logs[-1000:]
    
    def _is_trading_time(self):
        """判断是否在交易时间内"""
        now = datetime.now().time()
        date = datetime.now().date()
        
        # 判断是否是周末
        if date.weekday() >= 5:
            return False
        
        # 判断是否在交易时段内
        morning = TRADING_HOURS['morning_start'] <= now <= TRADING_HOURS['morning_end']
        afternoon = TRADING_HOURS['afternoon_start'] <= now <= TRADING_HOURS['afternoon_end']
        
        return morning or afternoon
    
    def _check_daily_trade_limit(self):
        """检查每日交易次数限制"""
        today = datetime.now().date()
        if today != self.today_date:
            self.daily_trades = 0
            self.today_date = today
        
        if self.daily_trades >= self.risk_config['max_daily_trades']:
            self._log(f"每日交易次数已达上限: {self.daily_trades}", 'WARNING')
            return False
        
        return True
    
    def _check_position_limit(self, stock_code, volume, is_buy=True):
        """检查持仓限制"""
        account = self.trading_api.get_account_balance()
        if not account:
            return False, "无法获取账户信息"
        
        total_assets = account.get('total_assets', 0)
        
        # 获取当前价格
        price_info = self.trading_api.get_real_time_price(stock_code)
        price = price_info.get('price', 0)
        if price <= 0:
            return False, "无法获取股票价格"
        
        # 计算交易金额
        trade_amount = price * volume * 100
        
        # 检查单只股票持仓比例
        current_positions = self.trading_api.get_positions()
        stock_value = sum(p['current_value'] for p in current_positions if p['stock_code'] == stock_code)
        
        if is_buy:
            new_stock_value = stock_value + trade_amount
            if new_stock_value / total_assets > self.risk_config['max_single_position_ratio']:
                return False, f"单只股票持仓比例超限 ({new_stock_value/total_assets:.1%} > {self.risk_config['max_single_position_ratio']:.1%})"
        
        # 检查总持仓比例
        positions_value = account.get('positions_value', 0)
        if is_buy:
            new_total_positions = positions_value + trade_amount
            if new_total_positions / total_assets > self.risk_config['max_total_position_ratio']:
                return False, f"总持仓比例超限 ({new_total_positions/total_assets:.1%} > {self.risk_config['max_total_position_ratio']:.1%})"
        
        # 检查可用余额
        balance = account.get('balance', 0)
        if is_buy and trade_amount > balance:
            return False, f"可用余额不足: 需要 {trade_amount:.2f}，可用 {balance:.2f}"
        
        return True, ""
    
    def _check_stop_loss(self, position):
        """检查是否需要止损"""
        profit_pct = position.get('profit_pct', 0)
        if profit_pct <= -self.risk_config['stop_loss_pct'] * 100:
            return True, f"触发止损: {profit_pct:.1%}"
        return False, ""
    
    def _check_take_profit(self, position):
        """检查是否需要止盈"""
        profit_pct = position.get('profit_pct', 0)
        if profit_pct >= self.risk_config['take_profit_pct'] * 100:
            return True, f"触发止盈: {profit_pct:.1%}"
        return False, ""
    
    def _generate_signals(self):
        """生成交易信号（AI策略）"""
        scan_cycle = 0
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            
            try:
                # 获取监控的股票列表
                stocks_to_monitor = self.ai_strategy.get_stocks_to_monitor() if hasattr(self.ai_strategy, 'get_stocks_to_monitor') else []
                
                if not stocks_to_monitor:
                    stocks_to_monitor = ['600519', '601318', '000858', '002594']
                
                scan_cycle += 1
                new_signals = 0
                # 对每个股票生成信号
                for stock_code in stocks_to_monitor:
                    try:
                        # 使用AI策略生成信号
                        signal = self.ai_strategy.generate_signal(stock_code)
                        
                        if signal and signal.signal_type in ['BUY', 'SELL']:
                            # 只添加高置信度信号
                            if signal.confidence >= 0.6:
                                self.signal_queue.put(signal)
                                new_signals += 1
                                self._log(f"生成信号: {signal.signal_type} {stock_code} 置信度:{signal.confidence:.1%}")
                        
                    except Exception as e:
                        self._log(f"生成信号失败 {stock_code}: {e}", 'ERROR')
                
                if scan_cycle % 1 == 0 or new_signals:
                    self._log(f"第{scan_cycle}轮扫描完成：监控 {len(stocks_to_monitor)} 只，新增信号 {new_signals} 个（每30秒扫描）")
                
            except Exception as e:
                self._log(f"信号生成线程异常: {e}", 'ERROR')
            
            # 每30秒生成一次信号
            time.sleep(30)
    
    def _is_trading_window_open(self):
        """是否应实际执行交易（交易时段，或模拟盘允许非交易时段）"""
        if self.allow_off_hours:
            return True
        return self._is_trading_time()
    
    def _monitor_positions(self):
        """监控持仓状态（止损/止盈）"""
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            
            try:
                positions = self.trading_api.get_positions()
                
                for position in positions:
                    stock_code = position['stock_code']
                    
                    # 检查止损
                    stop_loss, reason = self._check_stop_loss(position)
                    if stop_loss:
                        self._log(f"{stock_code} {reason}，自动卖出", 'WARNING')
                        self.signal_queue.put(TradingSignal(
                            stock_code=stock_code,
                            signal_type='SELL',
                            confidence=0.9,
                            reason=reason
                        ))
                        continue
                    
                    # 检查止盈
                    take_profit, reason = self._check_take_profit(position)
                    if take_profit:
                        self._log(f"{stock_code} {reason}，自动卖出", 'INFO')
                        self.signal_queue.put(TradingSignal(
                            stock_code=stock_code,
                            signal_type='SELL',
                            confidence=0.85,
                            reason=reason
                        ))
                
                # 更新持仓记录
                self.last_positions = {p['stock_code']: p for p in positions}
                
            except Exception as e:
                self._log(f"持仓监控线程异常: {e}", 'ERROR')
            
            # 每10秒检查一次持仓
            time.sleep(10)
    
    def _execute_signals(self):
        """执行交易信号"""
        exec_cycle = 0
        last_snapshot = 0.0
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            
            # 检查是否在交易时间
            if not self._is_trading_window_open():
                self._log("当前非交易时段，等待开市（模拟盘请启用允许非交易时段交易）", 'INFO')
                time.sleep(30)
                continue
            
            try:
                exec_cycle += 1
                # 每30秒输出一次账户快照，让日志实时可见
                now_ts = time.time()
                if now_ts - last_snapshot >= 30:
                    last_snapshot = now_ts
                    try:
                        acc = self.trading_api.get_account_balance()
                        pos = self.trading_api.get_positions()
                        bal = acc.get('balance', 0) if acc else 0
                        assets = acc.get('total_assets', bal) if acc else 0
                        npos = len(pos) if pos else 0
                        self._log(f"账户快照：总资产 {assets:.2f}，可用 {bal:.2f}，持仓 {npos} 只")
                    except Exception as e:
                        self._log(f"账户快照失败: {e}", 'WARNING')
                # 处理信号队列
                while not self.signal_queue.empty():
                    signal = self.signal_queue.get()
                    
                    if not self.trading_enabled:
                        self._log(f"交易已禁用，跳过信号: {signal.signal_type} {signal.stock_code}", 'WARNING')
                        continue
                    
                    # 检查每日交易限制
                    if not self._check_daily_trade_limit():
                        self._log(f"每日交易次数超限，跳过信号: {signal.signal_type} {signal.stock_code}", 'WARNING')
                        continue
                    
                    # 获取当前持仓
                    positions = self.trading_api.get_positions()
                    current_position = next((p for p in positions if p['stock_code'] == signal.stock_code), None)
                    
                    if signal.signal_type == 'BUY':
                        self._execute_buy(signal, current_position)
                    elif signal.signal_type == 'SELL':
                        self._execute_sell(signal, current_position)
                
            except Exception as e:
                self._log(f"信号执行线程异常: {e}", 'ERROR')
            
            # 每1秒检查一次队列
            time.sleep(1)
    
    def _execute_buy(self, signal, current_position):
        """执行买入操作"""
        try:
            # 获取实时价格
            price_info = self.trading_api.get_real_time_price(signal.stock_code)
            current_price = price_info.get('price', signal.price)
            
            if current_price <= 0:
                self._log(f"无法获取 {signal.stock_code} 价格，跳过买入", 'WARNING')
                return
            
            # 计算可买数量（按风险控制）
            account = self.trading_api.get_account_balance()
            if not account:
                self._log("无法获取账户信息，跳过买入", 'WARNING')
                return
            
            balance = account.get('balance', 0)
            total_assets = account.get('total_assets', balance)
            
            # 计算最大可买手数
            max_volume_by_balance = int(balance / (current_price * 100))
            max_volume_by_risk = int(total_assets * self.risk_config['max_single_position_ratio'] / (current_price * 100))
            
            # 如果已有持仓，计算剩余可买数量
            if current_position:
                current_value = current_position.get('current_value', 0)
                remaining_ratio = self.risk_config['max_single_position_ratio'] - (current_value / total_assets)
                max_volume_by_risk = int(total_assets * remaining_ratio / (current_price * 100))
            
            volume = max(1, min(max_volume_by_balance, max_volume_by_risk))
            
            if volume <= 0:
                self._log(f"{signal.stock_code} 可买数量为0，跳过买入", 'WARNING')
                return
            
            # 检查持仓限制
            ok, reason = self._check_position_limit(signal.stock_code, volume, is_buy=True)
            if not ok:
                hint = ''
                if '总持仓比例超限' in reason:
                    hint = '（已满仓，需等卖出机会或明日T+1解锁资金）'
                elif '单只股票持仓比例超限' in reason:
                    hint = '（该股已达单只持仓上限）'
                self._log(f"{signal.stock_code} 买入跳过: {reason}{hint}", 'WARNING')
                return
            
            # 执行买入
            order = self.trading_api.buy(
                stock_code=signal.stock_code,
                price=current_price,
                volume=volume,
                order_type='MARKET'
            )
            
            if order.status == 'FILLED':
                self.daily_trades += 1
                filled = order.filled_volume or volume
                self._log(f"[OK] 买入成功: {signal.stock_code} {filled}手 @ {current_price:.2f}")
            elif order.status == 'REJECTED':
                self._log(f"{signal.stock_code} 买入被拒: {order.message}", 'WARNING')
            else:
                self._log(f"[WARN] 买入订单已提交: {signal.stock_code} {volume}手，状态: {order.status}", 'INFO')
            
        except Exception as e:
            self._log(f"执行买入失败 {signal.stock_code}: {e}", 'ERROR')
    
    def _execute_sell(self, signal, current_position):
        """执行卖出操作"""
        try:
            # 检查是否有持仓
            if not current_position:
                self._log(f"{signal.stock_code} 没有持仓，跳过卖出", 'WARNING')
                return
            
            volume = current_position.get('volume', 0)
            if volume <= 0:
                self._log(f"{signal.stock_code} 持仓数量为0，跳过卖出", 'WARNING')
                return
            
            # 获取实时价格
            price_info = self.trading_api.get_real_time_price(signal.stock_code)
            current_price = price_info.get('price', 0)
            
            if current_price <= 0:
                self._log(f"无法获取 {signal.stock_code} 价格，跳过卖出", 'WARNING')
                return
            
            # 检查持仓限制
            ok, reason = self._check_position_limit(signal.stock_code, volume, is_buy=False)
            if not ok:
                self._log(f"{signal.stock_code} 持仓限制检查失败: {reason}", 'WARNING')
                return
            
            # 执行卖出
            order = self.trading_api.sell(
                stock_code=signal.stock_code,
                price=current_price,
                volume=volume,
                order_type='MARKET'
            )
            
            if order.status == 'FILLED':
                self.daily_trades += 1
                filled = order.filled_volume or volume
                profit = current_position.get('profit', 0)
                profit_pct = current_position.get('profit_pct', 0)
                self._log(f"[OK] 卖出成功: {signal.stock_code} {filled}手 @ {current_price:.2f}")
                self._log(f"   收益: {profit:+.2f} ({profit_pct:+.2f}%)")
            elif order.status == 'REJECTED':
                self._log(f"{signal.stock_code} 卖出被拒: {order.message}", 'WARNING')
            elif order.status == 'PARTIALLY_FILLED':
                self.daily_trades += 1
                self._log(f"[WARN] 卖出部分成交: {signal.stock_code} {order.filled_volume}手 @ {order.filled_price:.2f}", 'INFO')
            else:
                self._log(f"[WARN] 卖出订单已提交: {signal.stock_code} {volume}手，状态: {order.status}", 'INFO')
            
        except Exception as e:
            self._log(f"执行卖出失败 {signal.stock_code}: {e}", 'ERROR')
    
    def start(self):
        """启动交易引擎"""
        if self.running:
            self._log("交易引擎已在运行中", 'WARNING')
            return
        
        self.running = True
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_positions, daemon=True)
        self.monitor_thread.start()
        
        # 启动信号生成线程
        self.signal_thread = threading.Thread(target=self._generate_signals, daemon=True)
        self.signal_thread.start()
        
        # 启动信号执行线程
        self.executor_thread = threading.Thread(target=self._execute_signals, daemon=True)
        self.executor_thread.start()
        
        self._log("[RUN] 全自动交易引擎已启动")
        self._log(f"交易时间: 上午 {TRADING_HOURS['morning_start'].strftime('%H:%M')}-{TRADING_HOURS['morning_end'].strftime('%H:%M')}")
        self._log(f"          下午 {TRADING_HOURS['afternoon_start'].strftime('%H:%M')}-{TRADING_HOURS['afternoon_end'].strftime('%H:%M')}")
    
    def stop(self):
        """停止交易引擎"""
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.signal_thread:
            self.signal_thread.join(timeout=5)
        if self.executor_thread:
            self.executor_thread.join(timeout=5)
        
        self._log("🛑 全自动交易引擎已停止")
    
    def pause(self):
        """暂停交易"""
        self.paused = True
        self._log("⏸️ 交易已暂停")
    
    def resume(self):
        """恢复交易"""
        self.paused = False
        self._log("▶️ 交易已恢复")
    
    def enable_trading(self):
        """启用交易执行"""
        self.trading_enabled = True
        self._log("[OK] 交易执行已启用")
    
    def disable_trading(self):
        """禁用交易执行"""
        self.trading_enabled = False
        self._log("[ERROR] 交易执行已禁用（仅模拟）")
    
    def set_risk_config(self, **kwargs):
        """设置风险控制参数"""
        for key, value in kwargs.items():
            if key in self.risk_config:
                self.risk_config[key] = value
                self._log(f"风险参数更新: {key} = {value}")
    
    def get_status(self):
        """获取引擎状态"""
        return {
            'running': self.running,
            'paused': self.paused,
            'trading_enabled': self.trading_enabled,
            'daily_trades': self.daily_trades,
            'queue_size': self.signal_queue.qsize(),
            'is_trading_time': self._is_trading_time(),
            'risk_config': self.risk_config
        }
    
    def get_recent_logs(self, limit=50):
        """获取最近日志"""
        return self.trade_logs[-limit:]


class MockAIStrategy:
    """模拟AI策略（用于测试），可指定要监控的股票池"""
    
    def __init__(self, stocks=None):
        self.stocks = stocks or ['600519', '601318', '000858', '002594', '600036']
        self.signal_counter = 0
    
    def set_stocks(self, stocks):
        if stocks:
            self.stocks = list(stocks)
    
    def get_stocks_to_monitor(self):
        return self.stocks
    
    def generate_signal(self, stock_code):
        """生成模拟信号"""
        import random
        
        self.signal_counter += 1
        
        # 模拟信号生成
        rand = random.random()
        
        if rand < 0.15:
            # 15%概率买入
            return TradingSignal(
                stock_code=stock_code,
                signal_type='BUY',
                confidence=0.6 + random.random() * 0.35,
                reason=f"AI预测上涨，技术指标发出买入信号"
            )
        elif rand < 0.25:
            # 10%概率卖出
            return TradingSignal(
                stock_code=stock_code,
                signal_type='SELL',
                confidence=0.6 + random.random() * 0.35,
                reason=f"AI预测下跌，技术指标发出卖出信号"
            )
        else:
            # 75%概率持有或无信号
            return TradingSignal(
                stock_code=stock_code,
                signal_type='HOLD',
                confidence=0.5 + random.random() * 0.3,
                reason="当前趋势不明朗，建议观望"
            )


# 示例用法
if __name__ == '__main__':
    print("=" * 60)
    print("全自动交易引擎测试")
    print("=" * 60)
    
    # 创建模拟交易API
    from stock_trading_api import TradingAPIFactory
    trading_api = TradingAPIFactory.create_api('simulated', initial_balance=100000)
    
    # 创建模拟AI策略
    ai_strategy = MockAIStrategy()
    
    # 创建交易引擎
    engine = AutoTradingEngine(trading_api, ai_strategy)
    
    # 设置风险参数
    engine.set_risk_config(
        max_single_position_ratio=0.2,
        max_total_position_ratio=0.7,
        stop_loss_pct=0.05,
        take_profit_pct=0.08
    )
    
    print("\n启动交易引擎（按 Ctrl+C 停止）...")
    engine.start()
    
    try:
        while True:
            status = engine.get_status()
            print(f"\r状态: 运行={status['running']} 暂停={status['paused']} 交易={status['trading_enabled']} 队列={status['queue_size']} 今日交易={status['daily_trades']}", end='')
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\n停止交易引擎...")
        engine.stop()
        print("测试完成！")