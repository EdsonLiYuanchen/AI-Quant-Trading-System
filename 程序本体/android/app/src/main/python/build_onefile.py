# -*- coding: utf-8 -*-
import subprocess
import sys
import os

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 使用单文件模式打包
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--onefile',
    '--clean',
    '--name=AI_Trading_System',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    'launcher.py'
]

print(f"执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print(f"\n返回码: {result.returncode}")
if result.returncode != 0:
    print("STDOUT:", result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout)
    print("STDERR:", result.stderr[-5000:] if len(result.stderr) > 5000 else result.stderr)
else:
    print("打包成功!")
    dist_dir = os.path.join(BASE_DIR, 'dist')
    exe_path = os.path.join(dist_dir, 'AI_Trading_System.exe')
    if os.path.exists(exe_path):
        print(f"可执行文件: {exe_path}")
        print(f"文件大小: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")