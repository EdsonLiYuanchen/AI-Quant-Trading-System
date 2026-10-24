"""
测试所有可用的股票数据源
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import time
import akshare as ak

def test_all_stock_sources():
    """测试所有可用的股票数据源"""
    print("="*80)
    print("🧪 测试所有股票数据源")
    print("="*80)
    
    sources = [
        {'name': 'stock_zh_a_spot_em', 'func': ak.stock_zh_a_spot_em},
        {'name': 'stock_zh_a_spot', 'func': ak.stock_zh_a_spot},
        {'name': 'stock_sh_a_spot_em', 'func': ak.stock_sh_a_spot_em},
        {'name': 'stock_sz_a_spot_em', 'func': ak.stock_sz_a_spot_em},
        {'name': 'stock_kc_a_spot_em', 'func': ak.stock_kc_a_spot_em},
        {'name': 'stock_cy_a_spot_em', 'func': ak.stock_cy_a_spot_em},
        {'name': 'stock_bj_a_spot_em', 'func': ak.stock_bj_a_spot_em},
        {'name': 'stock_new_a_spot_em', 'func': ak.stock_new_a_spot_em},
    ]
    
    success_count = 0
    failed_count = 0
    
    for i, source in enumerate(sources):
        print(f"\n【测试 {i+1}/{len(sources)}】{source['name']}")
        try:
            start_time = time.time()
            df = source['func']()
            elapsed = time.time() - start_time
            
            if not df.empty:
                print(f"[OK] 成功! 获取 {len(df)} 条数据, 耗时 {elapsed:.2f}s")
                print(f"   列名: {df.columns.tolist()[:5]}...")
                success_count += 1
            else:
                print(f"[WARN] 返回空数据")
                failed_count += 1
                
        except Exception as e:
            print(f"[ERROR] 失败: {str(e)[:60]}...")
            failed_count += 1
        
        # 添加延迟避免限流
        time.sleep(2)
    
    print(f"\n" + "="*80)
    print(f"测试结果: [OK] {success_count} 成功, [ERROR] {failed_count} 失败")
    print("="*80)

if __name__ == "__main__":
    test_all_stock_sources()