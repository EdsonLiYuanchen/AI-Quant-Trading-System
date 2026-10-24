# -*- coding: utf-8 -*-
# 简化的启动器，只导入必要的模块
import sys
import os

print("启动AI量化交易系统...")
print(f"Python版本: {sys.version}")
print(f"工作目录: {os.getcwd()}")

try:
    # 添加当前目录到路径
    sys.path.append(os.path.dirname(__file__))
    print("路径添加成功")
    
    # 尝试导入主模块
    from AI量化交易系统GUI import main
    print("模块导入成功")
    
    # 运行主程序
    main()
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
    input("按Enter退出...")