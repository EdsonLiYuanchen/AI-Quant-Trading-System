# -*- coding: utf-8 -*-
import sys
import os

print("=== 直接运行GUI ===")

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

try:
    from AI量化交易系统GUI import main
    print("✓ 模块导入成功")
    print("正在启动GUI...")
    main()
except Exception as e:
    print(f"✗ 启动失败: {e}")
    import traceback
    traceback.print_exc()
    input("按Enter退出...")