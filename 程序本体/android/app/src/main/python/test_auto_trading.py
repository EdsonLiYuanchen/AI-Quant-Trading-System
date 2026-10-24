"""
全自动交易系统测试脚本
验证交易API和交易引擎的核心功能
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import time
import threading
from datetime import datetime

def test_trading_api():
    """测试交易API基本功能"""
    print("\n" + "=" * 60)
    print("测试1: 交易API基本功能")
    print("=" * 60)
    
    from stock_trading_api import TradingAPIFactory, ORDER_STATUS
    
    # 创建模拟交易API
    api = TradingAPIFactory.create_api('simulated', initial_balance=100000)
    
    print("\n1.1 获取账户信息")
    balance = api.get_account_balance()
    print(f"   初始总资产: {balance['total_assets']:.2f}")
    print(f"   初始余额: {balance['balance']:.2f}")
    
    # 测试买入
    print("\n1.2 测试买入")
    order = api.buy('600519', 0, 1, order_type='MARKET')  # 市价买入1手茅台
    if order:
        print(f"   订单ID: {order.order_id}")
        print(f"   状态: {ORDER_STATUS.get(order.status, order.status)}")
        print(f"   成交数量: {order.filled_volume}手")
        print(f"   成交价格: {order.filled_price:.2f}")
    
    # 获取持仓
    print("\n1.3 获取持仓")
    positions = api.get_positions()
    for pos in positions:
        print(f"   {pos['stock_code']} {pos['name']}: {pos['volume']}手 @ {pos['avg_cost']:.2f}")
    
    # 获取账户信息
    print("\n1.4 买入后账户信息")
    balance = api.get_account_balance()
    print(f"   总资产: {balance['total_assets']:.2f}")
    print(f"   持仓市值: {balance['positions_value']:.2f}")
    print(f"   可用余额: {balance['balance']:.2f}")
    
    # 测试卖出
    print("\n1.5 测试卖出")
    order = api.sell('600519', 0, 1, order_type='MARKET')  # 市价卖出1手茅台
    if order:
        print(f"   订单ID: {order.order_id}")
        print(f"   状态: {ORDER_STATUS.get(order.status, order.status)}")
        print(f"   成交数量: {order.filled_volume}手")
        print(f"   成交价格: {order.filled_price:.2f}")
    
    # 最终账户信息
    print("\n1.6 最终账户信息")
    balance = api.get_account_balance()
    print(f"   总资产: {balance['total_assets']:.2f}")
    print(f"   总收益: {balance['total_profit']:+.2f} ({balance['total_profit_pct']:+.2f}%)")
    
    # 测试交易历史
    print("\n1.7 交易历史")
    history = api.get_trade_history()
    for trade in history:
        print(f"   {trade['date']} {trade['side']} {trade['stock_code']} {trade['volume']}手 @ {trade['price']:.2f}")
    
    print("\n[OK] 交易API测试完成")


def test_auto_trading_engine():
    """测试全自动交易引擎"""
    print("\n" + "=" * 60)
    print("测试2: 全自动交易引擎")
    print("=" * 60)
    
    from stock_trading_api import TradingAPIFactory
    from auto_trading_engine import AutoTradingEngine, MockAIStrategy, TradingSignal
    
    # 创建交易API和策略
    trading_api = TradingAPIFactory.create_api('simulated', initial_balance=100000)
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
    
    # 启动引擎
    print("\n2.1 启动交易引擎")
    engine.start()
    
    # 运行一段时间进行测试
    print("\n2.2 运行交易引擎10秒...")
    time.sleep(10)
    
    # 获取引擎状态
    print("\n2.3 引擎状态")
    status = engine.get_status()
    print(f"   运行中: {status['running']}")
    print(f"   已暂停: {status['paused']}")
    print(f"   交易启用: {status['trading_enabled']}")
    print(f"   今日交易: {status['daily_trades']}笔")
    print(f"   信号队列: {status['queue_size']}个")
    
    # 获取账户信息
    print("\n2.4 账户信息")
    balance = trading_api.get_account_balance()
    print(f"   总资产: {balance['total_assets']:.2f}")
    print(f"   可用余额: {balance['balance']:.2f}")
    print(f"   持仓市值: {balance['positions_value']:.2f}")
    
    # 获取持仓
    print("\n2.5 当前持仓")
    positions = trading_api.get_positions()
    if positions:
        for pos in positions:
            print(f"   {pos['stock_code']} {pos['name']}: {pos['volume']}手")
            print(f"      成本价: {pos['avg_cost']:.2f}")
            print(f"      当前价: {pos['current_price']:.2f}")
            print(f"      盈亏: {pos['profit']:+.2f} ({pos['profit_pct']:+.2f}%)")
    else:
        print("   暂无持仓")
    
    # 获取日志
    print("\n2.6 交易日志(最近10条)")
    logs = engine.get_recent_logs(limit=10)
    for log in reversed(logs):
        print(f"   [{log['timestamp']}] [{log['level']}] {log['message']}")
    
    # 停止引擎
    print("\n2.7 停止交易引擎")
    engine.stop()
    
    print("\n[OK] 全自动交易引擎测试完成")


def test_trading_signal():
    """测试交易信号生成"""
    print("\n" + "=" * 60)
    print("测试3: 交易信号生成")
    print("=" * 60)
    
    from auto_trading_engine import MockAIStrategy, TradingSignal
    
    strategy = MockAIStrategy()
    
    print("\n3.1 生成测试信号")
    stocks = ['600519', '601318', '000858']
    
    for stock in stocks:
        signal = strategy.generate_signal(stock)
        print(f"   {stock}: {signal.signal_type} (置信度: {signal.confidence:.2%})")
        if signal.reason:
            print(f"      原因: {signal.reason}")
    
    print("\n[OK] 交易信号测试完成")


def test_risk_management():
    """测试风险控制功能"""
    print("\n" + "=" * 60)
    print("测试4: 风险控制功能")
    print("=" * 60)
    
    from stock_trading_api import TradingAPIFactory
    from auto_trading_engine import AutoTradingEngine, MockAIStrategy
    
    # 创建交易API和策略
    trading_api = TradingAPIFactory.create_api('simulated', initial_balance=50000)
    ai_strategy = MockAIStrategy()
    
    # 创建交易引擎
    engine = AutoTradingEngine(trading_api, ai_strategy)
    
    # 设置严格的风险参数
    engine.set_risk_config(
        max_single_position_ratio=0.1,  # 单股最大10%
        max_total_position_ratio=0.5,   # 总持仓最大50%
        stop_loss_pct=0.02,             # 止损2%
        take_profit_pct=0.03            # 止盈3%
    )
    
    # 启动引擎
    engine.start()
    
    print("\n4.1 测试风险控制（运行15秒）")
    time.sleep(15)
    
    # 检查账户信息
    balance = trading_api.get_account_balance()
    print(f"\n4.2 风险控制结果")
    print(f"   总资产: {balance['total_assets']:.2f}")
    print(f"   持仓市值: {balance['positions_value']:.2f}")
    print(f"   持仓比例: {(balance['positions_value']/balance['total_assets']*100):.1f}% (限制: 50%)")
    
    # 检查持仓
    positions = trading_api.get_positions()
    if positions:
        for pos in positions:
            pos_ratio = pos['current_value'] / balance['total_assets'] * 100
            print(f"\n   {pos['stock_code']} {pos['name']}")
            print(f"      持仓比例: {pos_ratio:.1f}% (限制: 10%)")
            print(f"      盈亏: {pos['profit']:+.2f} ({pos['profit_pct']:+.2f}%)")
    
    # 停止引擎
    engine.stop()
    
    print("\n[OK] 风险控制测试完成")


def test_ai_strategy_integration():
    """测试AI策略集成"""
    print("\n" + "=" * 60)
    print("测试5: AI策略集成")
    print("=" * 60)
    
    from stock_trading_api import TradingAPIFactory
    from auto_trading_engine import AutoTradingEngine, MockAIStrategy, TradingSignal
    
    # 创建交易API
    trading_api = TradingAPIFactory.create_api('simulated', initial_balance=100000)
    
    # 创建自定义策略
    class TestStrategy(MockAIStrategy):
        """测试策略：每隔一段时间生成一个买入信号"""
        
        def __init__(self):
            super().__init__()
            self.counter = 0
        
        def generate_signal(self, stock_code):
            self.counter += 1
            
            # 每5次调用生成一个买入信号
            if self.counter % 5 == 0:
                return TradingSignal(
                    stock_code=stock_code,
                    signal_type='BUY',
                    confidence=0.85,
                    reason=f"测试策略：第{self.counter}次调用，生成买入信号"
                )
            else:
                return TradingSignal(
                    stock_code=stock_code,
                    signal_type='HOLD',
                    confidence=0.6,
                    reason="测试策略：持有观望"
                )
    
    # 创建交易引擎
    strategy = TestStrategy()
    engine = AutoTradingEngine(trading_api, strategy)
    
    # 启动引擎
    engine.start()
    
    print("\n5.1 测试自定义AI策略（运行20秒）")
    time.sleep(20)
    
    # 检查交易次数
    status = engine.get_status()
    print(f"\n5.2 策略执行结果")
    print(f"   今日交易: {status['daily_trades']}笔")
    
    # 获取持仓
    positions = trading_api.get_positions()
    print(f"\n5.3 持仓情况")
    if positions:
        for pos in positions:
            print(f"   {pos['stock_code']} {pos['name']}: {pos['volume']}手")
    else:
        print("   暂无持仓")
    
    # 停止引擎
    engine.stop()
    
    print("\n[OK] AI策略集成测试完成")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("[RUN] 全自动交易系统测试套件")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        test_trading_api()
        test_trading_signal()
        test_auto_trading_engine()
        test_risk_management()
        test_ai_strategy_integration()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()