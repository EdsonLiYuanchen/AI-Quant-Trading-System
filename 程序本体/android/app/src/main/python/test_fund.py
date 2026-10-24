"""
测试基金管理功能
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from 持仓管理 import FundManager, FundPosition
from datetime import datetime

def test_fund_manager():
    """测试基金管理器"""
    print("="*80)
    print("测试基金管理功能")
    print("="*80)

    # 创建基金管理器
    fund_mgr = FundManager('test_fund_portfolio.pkl')

    # 测试添加持仓
    print("\n【测试1】添加基金持仓")
    print("-"*80)

    fund_mgr.add_position('159915', '创业板ETF', 1000.0, 2.3560)
    fund_mgr.add_position('159949', '创业板50ETF', 1500.0, 1.8765)
    fund_mgr.add_position('510050', '上证50ETF', 2000.0, 3.1234)

    fund_mgr.display_portfolio()

    # 测试更新净值
    print("\n【测试2】更新基金净值")
    print("-"*80)

    nav_updates = {
        '159915': 2.4567,
        '159949': 1.9234,
        '510050': 3.2345
    }

    fund_mgr.update_all_nav(nav_updates)
    fund_mgr.display_portfolio()

    # 测试部分卖出
    print("\n【测试3】卖出部分份额")
    print("-"*80)

    fund_mgr.reduce_position('159915', 500.0, 2.4567)
    fund_mgr.display_portfolio()

    # 测试全部卖出
    print("\n【测试4】卖出全部份额")
    print("-"*80)

    fund_mgr.reduce_position('510050', 2000.0, 3.2345)
    fund_mgr.display_portfolio()

    # 显示交易历史
    print("\n【交易历史】")
    print("-"*80)
    for record in fund_mgr.history[-5:]:
        action = "买入" if record['action'] == 'buy' else "卖出"
        print(f"{record['date']} {action} {record['fund_name']}({record['fund_code']}) "
              f"{record['volume']:.2f}份 @ {record['nav']:.4f} = {record['amount']:,.2f}元")

    # 测试清空
    print("\n【测试5】清空持仓")
    print("-"*80)
    fund_mgr.clear_portfolio()
    fund_mgr.display_portfolio()

    print("\n" + "="*80)
    print("测试完成!")
    print("="*80)

    # 清理测试文件
    try:
        os.remove('test_fund_portfolio.pkl')
        os.remove('test_fund_portfolio.json')
        print("\n测试文件已清理")
    except:
        pass

if __name__ == "__main__":
    test_fund_manager()
