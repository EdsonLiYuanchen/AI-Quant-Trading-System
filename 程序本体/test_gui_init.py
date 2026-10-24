# -*- coding: utf-8 -*-
import sys
import os

# 设置路径
sys.path.insert(0, r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

import queue
import tkinter as tk

# 导入GUI类
from AI量化交易系统GUI import AIQuantTradingGUI

def test_gui_init():
    print("=== 测试GUI初始化 ===")
    
    # 创建Tkinter根窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏窗口
    
    try:
        # 创建GUI实例
        gui = AIQuantTradingGUI(root)
        print("✓ GUI初始化成功")
        
        # 检查关键属性
        assert hasattr(gui, 'output_queue'), "缺少 output_queue 属性"
        assert hasattr(gui, 'crawler'), "缺少 crawler 属性"
        print("✓ 关键属性检查通过")
        
        # 检查爬虫类型
        if gui.crawler is not None:
            print(f"✓ 爬虫已加载: {type(gui.crawler).__name__}")
        else:
            print("✗ 爬虫加载失败")
        
        print("\n=== 测试通过 ===")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        root.destroy()

if __name__ == '__main__':
    success = test_gui_init()
    sys.exit(0 if success else 1)