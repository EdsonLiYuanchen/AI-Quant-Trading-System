# -*- coding: utf-8 -*-
import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext

sys.path.insert(0, r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

print("=== 测试GUI初始化 ===")

try:
    # 创建Tkinter根窗口
    root = tk.Tk()
    root.title("测试GUI")
    root.geometry("1400x900")
    
    # 创建一个简单的界面来测试
    main_container = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # 左侧面板
    left_panel = ttk.Frame(main_container, width=400)
    main_container.add(left_panel, weight=1)
    
    # 右侧面板
    right_panel = ttk.Frame(main_container, width=1000)
    main_container.add(right_panel, weight=3)
    
    # 在左侧添加一个标签
    label = ttk.Label(left_panel, text="左侧面板", font=("Arial", 14, "bold"))
    label.pack(pady=20)
    
    # 在右侧添加一个文本框
    output_text = scrolledtext.ScrolledText(
        right_panel,
        wrap=tk.WORD,
        font=("Consolas", 10),
        bg="#1e1e1e",
        fg="#d4d4d4"
    )
    output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    output_text.insert(tk.END, "测试界面显示正常！\n")
    
    print("✓ 基础GUI创建成功")
    
    # 显示窗口
    root.update()
    print("✓ 窗口更新成功")
    
    # 检查窗口是否可见
    print(f"窗口宽度: {root.winfo_width()}")
    print(f"窗口高度: {root.winfo_height()}")
    
    # 等待用户确认
    print("\n如果能看到界面，请关闭窗口继续...")
    root.mainloop()
    
    print("✓ GUI测试完成")
    
except Exception as e:
    print(f"✗ GUI测试失败: {e}")
    import traceback
    traceback.print_exc()