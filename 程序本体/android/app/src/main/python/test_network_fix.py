#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试网络连接修复
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from 实时行情增强 import RealtimeDataEnhancer

def test_market_overview():
    """测试市场概览功能"""
    print("🧪 测试市场概览功能...")
    
    enhancer = RealtimeDataEnhancer()
    
    try:
        overview = enhancer.get_market_overview_realtime()
        
        if overview:
            print("[OK] 市场概览测试成功！")
            print(f"更新时间: {overview.get('update_time', 'N/A')}")
            print(f"股票总数: {overview.get('total_stocks', 0)}")
            print(f"上涨家数: {overview.get('up_count', 0)}")
            print(f"下跌家数: {overview.get('down_count', 0)}")
            
            # 检查指数数据
            sh_index = overview.get('shanghai_index')
            if sh_index:
                print(f"上证指数: {sh_index.get('price', 'N/A')} ({sh_index.get('change', 'N/A')}%)")
            else:
                print("[WARN] 上证指数数据获取失败")
                
        else:
            print("[ERROR] 市场概览数据为空")
            
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")

def test_stock_data():
    """测试股票数据功能"""
    print("\n🧪 测试股票数据功能...")
    
    enhancer = RealtimeDataEnhancer()
    
    try:
        # 测试少量股票代码
        test_codes = ['000001', '000002']  # 平安银行、万科A
        df = enhancer.get_stock_realtime_batch(test_codes)
        
        if not df.empty:
            print("[OK] 股票数据测试成功！")
            print(f"获取到 {len(df)} 条股票数据")
            print("前几条数据:")
            print(df.head()[['代码', '名称', '最新价', '涨跌幅']])
        else:
            print("[ERROR] 股票数据为空")
            
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("网络连接修复测试")
    print("=" * 50)
    
    test_market_overview()
    test_stock_data()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)