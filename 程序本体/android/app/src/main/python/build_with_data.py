# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

BASE_DIR = os.path.abspath(r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

# 确保数据文件存在
data_cache_dir = os.path.join(BASE_DIR, 'data_cache')
if not os.path.exists(data_cache_dir):
    os.makedirs(data_cache_dir)

# 使用PyInstaller打包
cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    '--console',
    '--onefile',
    '--clean',
    '--name=AI_Trading_System',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    'launcher.py'
]

print(f"工作目录: {BASE_DIR}")
print(f"执行命令: {' '.join(cmd)}")

result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print(f"\n返回码: {result.returncode}")
if result.returncode != 0:
    print("STDOUT:", result.stdout[-8000:] if len(result.stdout) > 8000 else result.stdout)
    print("STDERR:", result.stderr[-8000:] if len(result.stderr) > 8000 else result.stderr)
else:
    print("打包成功!")
    dist_path = os.path.join(BASE_DIR, 'dist', 'AI_Trading_System.exe')
    if os.path.exists(dist_path):
        print(f"生成的可执行文件: {dist_path}")
        print(f"文件大小: {os.path.getsize(dist_path) / (1024*1024):.2f} MB")