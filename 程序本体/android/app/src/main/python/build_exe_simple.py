# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 简化版打包脚本
"""

import os
import shutil

# 设置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
BUILD_DIR = os.path.join(BASE_DIR, 'build')
SPEC_FILE = os.path.join(BASE_DIR, 'trading_system.spec')

# 清理旧的构建文件
if os.path.exists(DIST_DIR):
    shutil.rmtree(DIST_DIR)
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
if os.path.exists(SPEC_FILE):
    os.remove(SPEC_FILE)

# 使用PyInstaller命令行直接打包
import subprocess
import sys

cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--onefile',
    '--windowed',
    '--name=AI量化交易系统',
    '--clean',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    '--hidden-import=akshare',
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=tkinter',
    '--hidden-import=ttkbootstrap',
    '--hidden-import=sqlalchemy',
    '--hidden-import=requests',
    '--hidden-import=lxml',
    '--hidden-import=bs4',
    '--hidden-import=matplotlib',
    '--hidden-import=sklearn',
    '--hidden-import=win32com',
    '--hidden-import=pywin32',
    'start_gui.py'
]

print(f"执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\n返回码: {result.returncode}")