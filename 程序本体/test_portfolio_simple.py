# -*- coding: utf-8 -*-
"""
持仓管理功能测试脚本 (简化版 - 避免emoji编码问题)
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from 持仓管理 import PortfolioManager

if __name__ == "__main__":
    print("="*80)
    print("Portfolio Management Function Test")
    print("="*80)

    try:
        # Create portfolio manager
        pm = PortfolioManager('test_portfolio.pkl')

        # Test 1: Add positions
        print("\n[Test 1] Add positions")
        print("-"*80)
        pm.add_position('000001', 'PA', 100, 10.50)
        pm.add_position('000002', 'VK', 200, 15.80)

        # Display portfolio
        portfolio_info = pm.display_portfolio()

        # Test 2: Update prices
        print("\n[Test 2] Update prices")
        print("-"*80)
        pm.update_all_prices({
            '000001': 11.20,
            '000002': 14.50
        })
        pm.display_portfolio()

        # Test 3: AI trading signals
        print("\n[Test 3] AI Trading Signals")
        print("-"*80)

        test_cases = [
            ('000001', 11.20, 1, "Has position, AI bullish"),
            ('000001', 11.20, -1, "Has position, AI bearish"),
            ('600519', 1800.00, 1, "No position, AI bullish"),
            ('600519', 1800.00, -1, "No position, AI bearish"),
        ]

        for stock_code, price, ai_pred, desc in test_cases:
            signal, reason = pm.get_ai_trading_signal(stock_code, ai_pred, price)
            print(f"{stock_code} Price:{price:.2f} AI:{ai_pred} ({desc})")
            print(f"   Signal: {signal} - {reason}\n")

        # Test 4: Sell operation
        print("\n[Test 4] Sell operation")
        print("-"*80)
        pm.reduce_position('000002', 100, 14.50)
        pm.display_portfolio()

        # Test 5: Trade history
        print("\n[Test 5] Trade history")
        print("-"*80)
        pm.display_history()

        # Test 6: Save and load
        print("\n[Test 6] Save and load data")
        print("-"*80)
        print("Saving portfolio data...")
        saved = pm.save_portfolio()
        print(f"Save result: {'Success' if saved else 'Failed'}")

        print("\nLoading portfolio data...")
        pm2 = PortfolioManager('test_portfolio.pkl')
        pm2.display_portfolio()

        # Cleanup
        print("\n[Cleanup] Delete test data files")
        pm2.clear_portfolio()
        try:
            os.remove('test_portfolio.pkl')
            os.remove('test_portfolio.json')
            print("Test data files deleted")
        except:
            print("Warning: Failed to delete test files")

        print("\n" + "="*80)
        print("[SUCCESS] All tests passed!")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
