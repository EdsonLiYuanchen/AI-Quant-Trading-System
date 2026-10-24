"""
测试单个API接口的网络连接
用于调试网络问题
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import time
import akshare as ak

def test_single_api():
    """测试单个API接口"""
    print("="*80)
    print("🧪 测试单个API接口")
    print("="*80)
    
    # 测试1: 指数数据
    print("\n【测试1】获取指数数据")
    try:
        print("正在获取指数数据...")
        df = ak.stock_zh_index_spot_em()
        if not df.empty:
            print(f"[OK] 成功获取 {len(df)} 个指数")
            print(df[['代码', '名称', '最新价']].head())
        else:
            print("[ERROR] 返回空数据")
    except Exception as e:
        print(f"[ERROR] 获取指数数据失败: {e}")
    
    time.sleep(5)
    
    # 测试2: 股票数据（只获取少量）
    print("\n【测试2】获取股票数据")
    try:
        print("正在获取股票数据...")
        df = ak.stock_zh_a_spot_em()
        if not df.empty:
            print(f"[OK] 成功获取 {len(df)} 只股票")
            print(df[['代码', '名称', '最新价', '涨跌幅']].head())
        else:
            print("[ERROR] 返回空数据")
    except Exception as e:
        print(f"[ERROR] 获取股票数据失败: {e}")
    
    print("\n" + "="*80)
    print("[OK] 测试完成")
    print("="*80)

if __name__ == "__main__":
    test_single_api()