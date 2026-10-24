# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

BASE_DIR = os.path.abspath(r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

# 清理旧的dist和build目录
for dir_name in ['dist', 'build']:
    dir_path = os.path.join(BASE_DIR, dir_name)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
        print(f"已清理: {dir_path}")

# 使用PyInstaller打包，非单文件模式
cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    '--console',
    '--clean',
    '--name=AI_Trading_System',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    '--collect-all=tkinter',
    '--collect-all=pandas',
    '--collect-all=numpy',
    '--collect-all=akshare',
    'launcher.py'
]

print(f"\n工作目录: {BASE_DIR}")
print(f"执行命令: {' '.join(cmd)}")

result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print(f"\n返回码: {result.returncode}")
if result.returncode != 0:
    print("STDOUT:", result.stdout[-8000:] if len(result.stdout) > 8000 else result.stdout)
    print("STDERR:", result.stderr[-8000:] if len(result.stderr) > 8000 else result.stderr)
else:
    print("打包成功!")
    dist_dir = os.path.join(BASE_DIR, 'dist', 'AI_Trading_System')
    exe_path = os.path.join(dist_dir, 'AI_Trading_System.exe')
    if os.path.exists(exe_path):
        print(f"生成的可执行文件: {exe_path}")
        print(f"文件大小: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")