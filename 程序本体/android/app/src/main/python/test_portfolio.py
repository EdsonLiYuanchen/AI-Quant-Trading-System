"""
持仓管理功能测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from 持仓管理 import PortfolioManager

def test_portfolio_manager():
    """测试持仓管理器"""

    print("="*80)
    print("[TEST] 持仓管理功能测试")
    print("="*80)

    # 创建测试持仓管理器
    pm = PortfolioManager('test_portfolio.pkl')

    # 测试1: 添加持仓
    print("\n【测试1】添加持仓")
    print("-"*80)
    pm.add_position('000001', '平安银行', 100, 10.50)
    pm.add_position('000002', '万科A', 200, 15.80)
    pm.add_position('600000', '浦发银行', 150, 6.50)

    # 显示组合
    pm.display_portfolio()

    # 测试2: 更新价格
    print("\n【测试2】更新价格")
    print("-"*80)
    pm.update_all_prices({
        '000001': 11.20,
        '000002': 14.50,
        '600000': 7.10
    })
    pm.display_portfolio()

    # 测试3: AI交易信号判断
    print("\n【测试3】AI交易信号判断")
    print("-"*80)

    test_cases = [
        ('000001', 11.20, 1, "有持仓,AI看涨"),
        ('000001', 11.20, -1, "有持仓,AI看跌"),
        ('000001', 11.20, 0, "有持仓,AI中性"),
        ('600519', 1800.00, 1, "无持仓,AI看涨"),
        ('600519', 1800.00, -1, "无持仓,AI看跌"),
    ]

    for stock_code, price, ai_pred, desc in test_cases:
        signal, reason = pm.get_ai_trading_signal(stock_code, ai_pred, price)
        print(f"{stock_code} 价格:{price:.2f} AI={ai_pred} ({desc})")
        print(f"   建议: {signal} - {reason}\n")

    # 测试4: 卖出操作
    print("\n【测试4】卖出操作")
    print("-"*80)
    pm.reduce_position('000002', 100, 14.50)
    pm.display_portfolio()

    # 测试5: 交易历史
    print("\n【测试5】交易历史")
    print("-"*80)
    pm.display_history()

    # 测试6: 数据保存和加载
    print("\n【测试6】数据保存和加载")
    print("-"*80)
    print("保存持仓数据...")
    saved = pm.save_portfolio()
    print(f"保存结果: {'成功' if saved else '失败'}")

    # 创建新的管理器加载数据
    print("\n加载持仓数据...")
    pm2 = PortfolioManager('test_portfolio.pkl')
    pm2.display_portfolio()

    # 清理测试数据
    print("\n【清理】删除测试数据文件")
    pm2.clear_portfolio()
    try:
        os.remove('test_portfolio.pkl')
        os.remove('test_portfolio.json')
        print("✓ 测试数据文件已删除")
    except:
        print("[WARN]  测试数据文件删除失败")

    print("\n" + "="*80)
    print("[OK] 所有测试完成!")
    print("="*80)


def test_ai_signal_logic():
    """测试AI信号逻辑的全面性"""

    print("\n" + "="*80)
    print("🧪 AI交易信号逻辑测试")
    print("="*80)

    pm = PortfolioManager('test_ai_signals.pkl')

    # 模拟不同持仓盈亏情况
    scenarios = [
        # (持仓, 成本价, 当前价, 盈亏%, AI预测, 场景描述)
        (True, 10.00, 8.00, -20.00, 1, "深度亏损+AI看涨"),
        (True, 10.00, 9.50, -5.00, 1, "小亏+AI看涨"),
        (True, 10.00, 10.50, 5.00, 1, "小幅盈利+AI看涨"),
        (True, 10.00, 11.50, 15.00, 1, "大幅盈利+AI看涨"),

        (True, 10.00, 8.00, -20.00, -1, "深度亏损+AI看跌"),
        (True, 10.00, 9.50, -5.00, -1, "小亏+AI看跌"),
        (True, 10.00, 10.50, 5.00, -1, "小幅盈利+AI看跌"),
        (True, 10.00, 11.50, 15.00, -1, "大幅盈利+AI看跌"),

        (True, 10.00, 12.00, 20.00, 0, "大幅盈利+AI中性"),
        (True, 10.00, 8.00, -20.00, 0, "深度亏损+AI中性"),
        (True, 10.00, 10.00, 0.00, 0, "持平+AI中性"),

        (False, 0, 10.00, 0, 1, "无持仓+AI看涨"),
        (False, 0, 10.00, 0, -1, "无持仓+AI看跌"),
        (False, 0, 10.00, 0, 0, "无持仓+AI中性"),
    ]

    print(f"\n{'场景':<25} {'持仓':<8} {'盈亏%':<10} {'AI预测':<10} {'信号':<10} {'理由'}")
    print("-"*100)

    for has_position, cost_price, current_price, profit_pct, ai_pred, scenario in scenarios:
        if has_position:
            # 创建测试持仓
            pm.add_position('TEST', '测试股票', 100, cost_price)
            pm.update_all_prices({'TEST': current_price})

        signal, reason = pm.get_ai_trading_signal('TEST', ai_pred, current_price)

        position_str = f"{100}手@{cost_price:.2f}" if has_position else "无"
        profit_str = f"{profit_pct:+.2f}%" if has_position else "-"
        ai_str = {1: "看涨", 0: "中性", -1: "看跌"}[ai_pred]

        print(f"{scenario:<25} {position_str:<8} {profit_str:<10} {ai_str:<10} {signal:<10} {reason}")

        # 清理
        if has_position and 'TEST' in pm.positions:
            del pm.positions['TEST']

    print("-"*100)

    # 清理测试数据
    pm.clear_portfolio()
    try:
        os.remove('test_ai_signals.pkl')
        os.remove('test_ai_signals.json')
    except:
        pass

    print("\n[OK] AI信号逻辑测试完成!")


if __name__ == "__main__":
    try:
        # 运行基本功能测试
        test_portfolio_manager()

        # 运行AI信号逻辑测试
        test_ai_signal_logic()

        print("\n" + "="*80)
        print("🎉 所有测试通过!")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
