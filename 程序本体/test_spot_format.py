"""
测试 stock_zh_a_spot 接口的返回格式
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import akshare as ak

def test_spot_format():
    """测试股票数据接口返回格式"""
    print("="*80)
    print("🧪 测试股票数据接口格式")
    print("="*80)
    
    try:
        df = ak.stock_zh_a_spot()
        print(f"\n[OK] 成功获取数据，共 {len(df)} 条")
        print("\n数据列名:")
        print(df.columns.tolist())
        print("\n前5行数据:")
        print(df.head())
        print("\n数据类型:")
        print(df.dtypes)
        
    except Exception as e:
        print(f"[ERROR] 获取失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("[OK] 测试完成")
    print("="*80)

if __name__ == "__main__":
    test_spot_format()