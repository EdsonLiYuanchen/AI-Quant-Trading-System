"""
测试网络连接增强功能
验证同花顺实时数据增强器的网络稳定性改进
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from tonghuashun_realtime import TonghuashunRealtimeEnhancer, TonghuashunDisplay

def test_network_enhancement():
    """测试网络连接增强功能"""
    print("="*80)
    print("🧪 测试同花顺实时数据网络连接增强功能")
    print("="*80)
    
    # 创建增强器和显示面板
    enhancer = TonghuashunRealtimeEnhancer()
    display = TonghuashunDisplay(enhancer)
    
    # 首先运行网络诊断
    print("\n【网络诊断】")
    enhancer.diagnose_network()
    
    # 测试1: 市场概览（最可能失败的操作）
    print("\n【测试1】获取市场概览...")
    try:
        overview = enhancer.get_market_overview_realtime()
        if overview:
            print(f"[OK] 市场概览获取成功")
            print(f"   更新时间: {overview.get('update_time', 'N/A')}")
            print(f"   总股票数: {overview.get('total_stocks', 0)}")
            print(f"   状态: {overview.get('status', 'online')}")
        else:
            print("[ERROR] 市场概览返回为空")
    except Exception as e:
        print(f"[ERROR] 市场概览获取失败: {e}")
    
    # 测试2: 指数实时行情
    print("\n【测试2】获取指数实时行情...")
    try:
        indexes = ['000001', '399001', '000300', '399006']
        df = enhancer.get_index_realtime(indexes)
        if not df.empty:
            print(f"[OK] 指数行情获取成功: {len(df)} 个指数")
            for _, row in df.iterrows():
                print(f"   {row['name']} ({row['symbol']}): {row['price']:.2f}")
        else:
            print("[WARN] 指数行情返回为空（可能使用离线数据）")
    except Exception as e:
        print(f"[ERROR] 指数行情获取失败: {e}")
    
    # 测试3: 股票实时行情
    print("\n【测试3】获取股票实时行情...")
    try:
        stocks = ['000001', '000002', '600000']
        df = enhancer.get_stock_realtime_batch(stocks)
        if not df.empty:
            print(f"[OK] 股票行情获取成功: {len(df)} 只股票")
        else:
            print("[WARN] 股票行情返回为空（可能使用离线数据）")
    except Exception as e:
        print(f"[ERROR] 股票行情获取失败: {e}")
    
    # 测试4: 基金实时行情
    print("\n【测试4】获取基金实时行情...")
    try:
        funds = ['510300', '159915']
        df = enhancer.get_fund_realtime_batch(funds)
        if not df.empty:
            print(f"[OK] 基金行情获取成功: {len(df)} 只基金")
        else:
            print("[WARN] 基金行情返回为空（可能使用离线数据）")
    except Exception as e:
        print(f"[ERROR] 基金行情获取失败: {e}")
    
    # 测试5: 概念板块行情
    print("\n【测试5】获取概念板块行情...")
    try:
        df = enhancer.get_concept_board_realtime()
        if not df.empty:
            print(f"[OK] 概念板块获取成功: {len(df)} 个板块")
        else:
            print("[WARN] 概念板块返回为空（可能使用离线数据）")
    except Exception as e:
        print(f"[ERROR] 概念板块获取失败: {e}")
    
    print("\n" + "="*80)
    print("[OK] 网络连接增强测试完成")
    print("="*80)

if __name__ == "__main__":
    test_network_enhancement()