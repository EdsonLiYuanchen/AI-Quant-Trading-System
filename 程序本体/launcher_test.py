# -*- coding: utf-8 -*-
import sys
import os

print("=== AI Trading System Test Launcher ===")
print(f"Python版本: {sys.version}")
print(f"工作目录: {os.getcwd()}")
print(f"脚本目录: {os.path.dirname(__file__)}")

try:
    # 添加当前目录到路径
    sys.path.append(os.path.dirname(__file__))
    print("1. 路径添加成功")
    
    # 尝试导入主模块
    print("2. 正在导入AI量化交易系统GUI...")
    from AI量化交易系统GUI import main
    print("3. 模块导入成功")
    
    # 不启动GUI，只测试到这里
    print("4. 测试通过！模块导入成功！")
    print("5. 如果要启动完整GUI，请运行完整版本")
    
except Exception as e:
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {e}")
    import traceback
    traceback.print_exc()
    input("按Enter退出...")