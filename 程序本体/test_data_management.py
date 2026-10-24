#!/usr/bin/env python3
"""
测试数据管理功能
创建一些测试文件来验证数据管理功能
"""

import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_test_files():
    """创建测试文件"""
    print("[FILE] 创建测试文件...")
    
    # 创建测试AI模型文件
    for i in range(5):
        model_data = {
            'model_type': f'test_model_{i}',
            'performance': np.random.random(),
            'created_at': datetime.now() - timedelta(days=i*10),
            'features': np.random.rand(100, 10)
        }
        
        filename = f'ai_model_test_{i}.pkl'
        with open(filename, 'wb') as f:
            pickle.dump(model_data, f)
        print(f"  ✓ 创建 {filename}")
    
    # 创建测试数据目录
    data_dir = "金融数据"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 创建测试股票数据文件
    for i in range(3):
        stock_code = f'00000{i+1}'
        df = pd.DataFrame({
            '日期': pd.date_range('2024-01-01', periods=100),
            '开盘': np.random.rand(100) * 100 + 10,
            '收盘': np.random.rand(100) * 100 + 10,
            '最高': np.random.rand(100) * 100 + 10,
            '最低': np.random.rand(100) * 100 + 10,
            '成交量': np.random.randint(1000000, 10000000, 100)
        })
        
        filename = f"{stock_code}_20240101_20241231.csv"
        filepath = os.path.join(data_dir, filename)
        df.to_csv(filepath, index=False)
        print(f"  ✓ 创建 {filepath}")
    
    # 创建测试分析数据目录
    analysis_dir = "分析数据"
    if not os.path.exists(analysis_dir):
        os.makedirs(analysis_dir)
    
    # 创建测试分析报告
    for i in range(2):
        report_data = {
            'stock_code': f'00000{i+1}',
            'analysis_date': datetime.now(),
            'results': {
                'profit': np.random.random() * 0.2,
                'risk': np.random.random() * 0.1,
                'accuracy': np.random.random() * 0.8 + 0.2
            }
        }
        
        filename = f"analysis_report_{i}.json"
        filepath = os.path.join(analysis_dir, filename)
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 创建 {filepath}")
    
    print("\n[OK] 测试文件创建完成！")
    print("现在可以启动GUI测试数据管理功能：")
    print("python AI量化交易系统GUI.py")

def cleanup_test_files():
    """清理测试文件"""
    print("\n🧹 清理测试文件...")
    
    # 删除模型文件
    import glob
    for pattern in ['ai_model_test_*.pkl', 'ai_model_*.pkl']:
        for filepath in glob.glob(pattern):
            try:
                os.remove(filepath)
                print(f"  ✓ 删除 {filepath}")
            except:
                pass
    
    # 删除数据目录
    for dir_name in ['金融数据', '分析数据']:
        if os.path.exists(dir_name):
            import shutil
            shutil.rmtree(dir_name)
            print(f"  ✓ 删除目录 {dir_name}")
    
    print("[OK] 清理完成！")

if __name__ == "__main__":
    print("[BOT] AI量化交易系统 - 数据管理功能测试")
    print("="*50)
    
    while True:
        print("\n选择操作:")
        print("1. 创建测试文件")
        print("2. 清理测试文件")
        print("3. 退出")
        
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == '1':
            create_test_files()
        elif choice == '2':
            cleanup_test_files()
        elif choice == '3':
            print("👋 再见！")
            break
        else:
            print("[ERROR] 无效选择，请重新输入")