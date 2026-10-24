# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 手动打包脚本
使用非单文件模式并手动复制akshare数据
"""

import subprocess
import sys
import os
import shutil

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'
DIST_DIR = os.path.join(BASE_DIR, 'dist', 'AI量化交易系统')

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

# 如果打包成功，手动复制akshare数据文件
if result.returncode == 0 and os.path.exists(DIST_DIR):
    print(f"\n复制akshare数据文件到 {DIST_DIR}")
    dest_akshare = os.path.join(DIST_DIR, 'akshare')
    dest_file_fold = os.path.join(dest_akshare, 'file_fold')
    
    if os.path.exists(dest_file_fold):
        shutil.rmtree(dest_file_fold)
    
    shutil.copytree(file_fold_dir, dest_file_fold)
    print(f"成功复制akshare数据文件")