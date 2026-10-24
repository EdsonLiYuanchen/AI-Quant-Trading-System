# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 非单文件打包脚本
包含akshare的file_fold数据目录
"""

import subprocess
import sys
import os

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 获取akshare的file_fold目录
import akshare
akshare_dir = os.path.dirname(akshare.__file__)
file_fold_dir = os.path.join(akshare_dir, 'file_fold')
print(f"akshare file_fold目录: {file_fold_dir}")

# 使用PyInstaller命令行直接打包（非单文件模式，带控制台）
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--clean',
    '--noconfirm',
    '--console',
    '--name=AI量化交易系统',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    f'--add-data={file_fold_dir};akshare/file_fold',
    '--onedir',  # 非单文件模式
    'start_gui.py'
]

print(f"执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print("STDOUT:")
print(result.stdout[-8000:] if len(result.stdout) > 8000 else result.stdout)
print("\nSTDERR:")
print(result.stderr[-8000:] if len(result.stderr) > 8000 else result.stderr)
print(f"\n返回码: {result.returncode}")