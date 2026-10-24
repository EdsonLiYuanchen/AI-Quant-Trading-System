# -*- coding: utf-8 -*-
import sys
import os

print("=== 诊断GUI问题 ===")

# 测试基础导入
print("\n1. 测试基础导入...")
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext
    print("✓ tkinter导入成功")
except Exception as e:
    print(f"✗ tkinter导入失败: {e}")

# 测试主模块导入
print("\n2. 测试主模块导入...")
sys.path.insert(0, r'C:\Users\Edson\code\.vscode\量化交易\程序本体')
try:
    from AI量化交易系统GUI import AIQuantTradingGUI
    print("✓ 主模块导入成功")
except Exception as e:
    print(f"✗ 主模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试GUI初始化
print("\n3. 测试GUI初始化...")
try:
    root = tk.Tk()
    root.withdraw()  # 隐藏窗口
    
    app = AIQuantTradingGUI(root)
    print("✓ GUI初始化成功")
    
    # 检查关键组件
    print("\n4. 检查关键组件...")
    assert hasattr(app, 'output_text'), "缺少 output_text"
    print("✓ output_text 存在")
    
    assert hasattr(app, 'output_queue'), "缺少 output_queue"
    print("✓ output_queue 存在")
    
    assert hasattr(app, 'crawler'), "缺少 crawler"
    print("✓ crawler 存在")
    
    # 测试日志功能
    print("\n5. 测试日志功能...")
    app.log("测试日志消息", "info")
    print("✓ 日志功能正常")
    
    root.destroy()
    print("\n=== 所有测试通过 ===")
    
except Exception as e:
    print(f"✗ GUI初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)