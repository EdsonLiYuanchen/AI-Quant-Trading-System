"""
测试替代数据源
尝试不同的akshare接口
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import time
import akshare as ak

def test_alternative_sources():
    """测试替代数据源"""
    print("="*80)
    print("🧪 测试替代数据源")
    print("="*80)
    
    # 测试1: 东方财富股票数据（旧接口）
    print("\n【测试1】东方财富股票数据 (stock_zh_a_spot)")
    try:
        print("正在获取...")
        df = ak.stock_zh_a_spot()
        if not df.empty:
            print(f"[OK] 成功获取 {len(df)} 只股票")
            print(df[['代码', '名称', '最新价']].head())
        else:
            print("[ERROR] 返回空数据")
    except Exception as e:
        print(f"[ERROR] 失败: {e}")
    
    time.sleep(3)
    
    # 测试2: 新浪股票数据
    print("\n【测试2】新浪股票数据 (stock_zh_a_spot_sina)")
    try:
        print("正在获取...")
        df = ak.stock_zh_a_spot_sina()
        if not df.empty:
            print(f"[OK] 成功获取 {len(df)} 只股票")
            print(df[['代码', '名称', '最新价']].head())
        else:
            print("[ERROR] 返回空数据")
    except Exception as e:
        print(f"[ERROR] 失败: {e}")
    
    time.sleep(3)
    
    # 测试3: 腾讯股票数据
    print("\n【测试3】腾讯股票数据 (stock_zh_a_spot_qq)")
    try:
        print("正在获取...")
        df = ak.stock_zh_a_spot_qq()
        if not df.empty:
            print(f"[OK] 成功获取 {len(df)} 只股票")
            print(df[['代码', '名称', '最新价']].head())
        else:
            print("[ERROR] 返回空数据")
    except Exception as e:
        print(f"[ERROR] 失败: {e}")
    
    time.sleep(3)
    
    # 测试4: 雪球股票数据
    print("\n【测试4】雪球股票数据 (stock_zh_a_spot_xueqiu)")
    try:
        print("正在获取...")
        df = ak.stock_zh_a_spot_xueqiu()
        if not df.empty:
            print(f"[OK] 成功获取 {len(df)} 只股票")
            print(df[['代码', '名称', '最新价']].head())
        else:
            print("[ERROR] 返回空数据")
    except Exception as e:
        print(f"[ERROR] 失败: {e}")
    
    print("\n" + "="*80)
    print("[OK] 测试完成")
    print("="*80)

if __name__ == "__main__":
    test_alternative_sources()