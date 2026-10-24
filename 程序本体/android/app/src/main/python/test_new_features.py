"""
测试新增功能：代理IP、缓存机制、限流检测
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import time
from tonghuashun_realtime import TonghuashunRealtimeEnhancer

def test_cache_feature():
    """测试缓存功能"""
    print("="*80)
    print("🧪 测试缓存功能")
    print("="*80)
    
    enhancer = TonghuashunRealtimeEnhancer(cache_ttl=60)
    
    # 第一次获取（应该不命中缓存）
    print("\n【第1次请求】")
    start_time = time.time()
    df = enhancer.get_stock_realtime_batch(['000001', '000002'])
    elapsed = time.time() - start_time
    print(f"耗时: {elapsed:.2f}s")
    
    # 第二次获取（应该命中缓存）
    print("\n【第2次请求】")
    start_time = time.time()
    df = enhancer.get_stock_realtime_batch(['000001', '000002'])
    elapsed = time.time() - start_time
    print(f"耗时: {elapsed:.2f}s")
    
    # 测试关闭缓存
    print("\n【关闭缓存请求】")
    start_time = time.time()
    df = enhancer.get_stock_realtime_batch(['000001', '000002'], use_cache=False)
    elapsed = time.time() - start_time
    print(f"耗时: {elapsed:.2f}s")

def test_proxy_feature():
    """测试代理功能"""
    print("\n" + "="*80)
    print("🧪 测试代理功能")
    print("="*80)
    
    # 测试无代理
    print("\n【无代理模式】")
    enhancer = TonghuashunRealtimeEnhancer()
    print(f"代理状态: {'已启用' if enhancer.proxy_enabled else '未启用'}")
    
    # 测试设置代理（示例代理，实际使用时替换）
    print("\n【设置代理】")
    enhancer.set_proxy('http://127.0.0.1:8888')
    print(f"代理状态: {'已启用' if enhancer.proxy_enabled else '未启用'}")
    
    # 测试禁用代理
    print("\n【禁用代理】")
    enhancer.set_proxy(None)
    print(f"代理状态: {'已启用' if enhancer.proxy_enabled else '未启用'}")

def test_rate_limit_detection():
    """测试限流检测功能"""
    print("\n" + "="*80)
    print("🧪 测试限流检测功能")
    print("="*80)
    
    enhancer = TonghuashunRealtimeEnhancer()
    
    # 模拟限流检测
    print("\n【模拟限流检测】")
    enhancer._detect_rate_limit("RemoteDisconnected")
    print(f"限流状态: {'已检测到限流' if enhancer.rate_limit_detected else '正常'}")
    
    # 检查限流状态
    print("\n【检查限流状态】")
    is_limited = enhancer._check_rate_limit()
    print(f"是否被限流: {is_limited}")
    
    # 测试缓存目录
    print("\n【缓存目录】")
    print(f"缓存目录: {enhancer.cache_dir}")
    print(f"缓存有效期: {enhancer.cache_ttl}秒")

if __name__ == "__main__":
    test_cache_feature()
    test_proxy_feature()
    test_rate_limit_detection()
    
    print("\n" + "="*80)
    print("[OK] 新功能测试完成")
    print("="*80)