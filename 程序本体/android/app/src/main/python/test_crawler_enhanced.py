# -*- coding: utf-8 -*-
import sys
import os

# 设置路径
sys.path.insert(0, r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

from 增强版数据爬取 import EnhancedDataCrawler

def test_crawler():
    print("=== 测试增强版数据爬取器 ===")
    
    # 创建爬虫实例，启用所有数据源
    crawler = EnhancedDataCrawler(use_all_sources=True)
    
    # 测试获取股票数据
    print("\n测试获取股票 600519 (贵州茅台) 数据...")
    try:
        df = crawler.get_stock_daily('600519', start_date='2024-01-01', end_date='2024-12-31')
        if df is not None and not df.empty:
            print(f"✓ 成功获取数据，共 {len(df)} 条记录")
            print(f"  数据源: {crawler.last_source}")
            print(f"  数据范围: {df.index.min().strftime('%Y-%m-%d')} 至 {df.index.max().strftime('%Y-%m-%d')}")
            print(f"  最新收盘价: {df['close'].iloc[-1]:.2f}")
        else:
            print("✗ 获取数据失败")
    except Exception as e:
        print(f"✗ 获取数据异常: {e}")
    
    # 测试获取多个股票数据
    print("\n测试批量获取股票数据...")
    stocks = ['600519', '000858', '601318']
    for stock in stocks:
        try:
            df = crawler.get_stock_daily(stock, start_date='2024-01-01', end_date='2024-01-15')
            if df is not None and not df.empty:
                print(f"✓ {stock}: 成功获取 {len(df)} 条记录")
            else:
                print(f"✗ {stock}: 获取失败")
        except Exception as e:
            print(f"✗ {stock}: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == '__main__':
    test_crawler()