# -*- coding: utf-8 -*-
"""创建桌面快捷方式"""

import os
import win32com.client

# 快捷方式信息
shortcut_path = os.path.join(os.environ['USERPROFILE'], 'Desktop', 'AI_Trading_System.lnk')
target_path = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\start_trading.bat'
working_dir = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 删除旧的快捷方式
if os.path.exists(shortcut_path):
    os.remove(shortcut_path)

# 创建快捷方式
shell = win32com.client.Dispatch("WScript.Shell")
shortcut = shell.CreateShortCut(shortcut_path)
shortcut.TargetPath = target_path
shortcut.WorkingDirectory = working_dir
shortcut.Description = "AI Trading System"
shortcut.Save()

print("Shortcut created at:", shortcut_path)
print("Target:", target_path)
print("Working directory:", working_dir)