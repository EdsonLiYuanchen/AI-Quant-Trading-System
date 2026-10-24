# -*- coding: utf-8 -*-
import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext

sys.path.insert(0, r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

print("=== 详细诊断GUI创建过程 ===")

try:
    # 创建根窗口
    root = tk.Tk()
    root.title("[BOT] AI量化交易系统 v2.0 - 测试")
    root.geometry("1400x900")
    print("✓ 根窗口创建成功")
    
    # 导入主模块
    from AI量化交易系统GUI import AIQuantTradingGUI
    print("✓ 模块导入成功")
    
    # 手动创建界面组件
    print("\n=== 手动创建界面组件 ===")
    
    # 1. 创建菜单
    print("1. 创建菜单...")
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="文件", menu=file_menu)
    file_menu.add_command(label="退出", command=root.quit)
    print("   ✓ 菜单创建成功")
    
    # 2. 创建主容器
    print("2. 创建主容器...")
    main_container = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    print("   ✓ 主容器创建成功")
    
    # 3. 创建左侧面板
    print("3. 创建左侧面板...")
    left_panel = ttk.Frame(main_container, width=400)
    main_container.add(left_panel, weight=1)
    
    # 添加标签页
    notebook = ttk.Notebook(left_panel)
    notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text="数据爬取")
    ttk.Label(tab1, text="数据爬取功能", font=("Arial", 12, "bold")).pack(pady=10)
    
    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text="AI回测")
    ttk.Label(tab2, text="AI回测功能", font=("Arial", 12, "bold")).pack(pady=10)
    print("   ✓ 左侧面板创建成功")
    
    # 4. 创建右侧面板
    print("4. 创建右侧面板...")
    right_panel = ttk.Frame(main_container, width=1000)
    main_container.add(right_panel, weight=3)
    
    # 输出文本框
    output_text = scrolledtext.ScrolledText(
        right_panel,
        wrap=tk.WORD,
        font=("Consolas", 10),
        bg="#1e1e1e",
        fg="#d4d4d4"
    )
    output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    output_text.insert(tk.END, "测试界面显示正常！\n")
    output_text.insert(tk.END, "如果能看到这个界面，说明GUI组件创建成功。\n")
    print("   ✓ 右侧面板创建成功")
    
    # 5. 更新窗口
    print("5. 更新窗口...")
    root.update()
    print(f"   窗口宽度: {root.winfo_width()}")
    print(f"   窗口高度: {root.winfo_height()}")
    print(f"   窗口可见: {root.winfo_visible()}")
    
    print("\n=== 测试完成 ===")
    print("如果能看到界面，请关闭窗口继续...")
    
    # 运行主循环
    root.mainloop()
    
    print("✓ GUI测试完成")
    
except Exception as e:
    print(f"✗ GUI创建失败: {e}")
    import traceback
    traceback.print_exc()
    input("按Enter退出...")