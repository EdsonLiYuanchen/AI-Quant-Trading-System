# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 打包脚本（不清理旧文件）
"""

import subprocess
import sys

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 使用PyInstaller命令行直接打包（简化版）
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--clean',
    '--noconfirm',
    '--name=AI量化交易系统',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    'start_gui.py'
]

print(f"执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print("STDOUT:")
print(result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout)
print("\nSTDERR:")
print(result.stderr[-5000:] if len(result.stderr) > 5000 else result.stderr)
print(f"\n返回码: {result.returncode}")