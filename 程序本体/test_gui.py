# -*- coding: utf-8 -*-
import sys
import os
import traceback

print("=== 详细测试GUI启动 ===")
print(f"Python版本: {sys.version}")
print(f"工作目录: {os.getcwd()}")

sys.path.append(os.path.dirname(__file__))

try:
    print("1. 导入基础模块...")
    import tkinter as tk
    print("   tkinter 导入成功")
    
    print("2. 导入金融数据模块...")
    from 爬取金融数据 import FinancialDataCrawler
    print("   爬取金融数据 导入成功")
    
    print("3. 导入AI交易模块...")
    from 多模型AI量化交易 import AI_MODELS, AITradingStrategy
    print("   多模型AI量化交易 导入成功")
    
    print("4. 导入GUI模块...")
    from AI量化交易系统GUI import AIQuantTradingGUI, main
    print("   AI量化交易系统GUI 导入成功")
    
    print("\n5. 尝试创建GUI对象...")
    root = tk.Tk()
    root.withdraw()  # 不显示窗口
    print("   创建Tkinter根窗口成功")
    
    app = AIQuantTradingGUI(root)
    print("   创建AIQuantTradingGUI对象成功")
    
    root.destroy()
    print("   销毁窗口成功")
    
    print("\n=== 所有测试通过! GUI应该能正常运行 ===")
    
except Exception as e:
    print(f"\n错误类型: {type(e).__name__}")
    print(f"错误信息: {e}")
    print("\n完整堆栈跟踪:")
    traceback.print_exc()
    input("按Enter退出...")