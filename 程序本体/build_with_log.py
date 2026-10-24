# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

BASE_DIR = os.path.abspath(r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

# akshare的file_fold目录
akshare_dir = os.path.join(sys.prefix, 'Lib', 'site-packages', 'akshare')
file_fold = os.path.join(akshare_dir, 'file_fold')

print(f"akshare目录: {akshare_dir}")
print(f"file_fold目录: {file_fold}")
print(f"file_fold存在: {os.path.exists(file_fold)}")

# 使用PyInstaller打包，单文件模式，添加akshare的file_fold
cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    '--console',
    '--onefile',
    '--clean',
    '--name=AI_Trading_System',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    f'--add-data={file_fold};akshare/file_fold',
    '--collect-all=tkinter',
    '--collect-all=pandas',
    '--collect-all=numpy',
    '--collect-all=akshare',
    '--collect-all=scipy',
    '--collect-all=sqlalchemy',
    'launcher.py'
]

print(f"\n工作目录: {BASE_DIR}")
print(f"执行命令: {' '.join(cmd)}")

# 保存日志
log_file = os.path.join(BASE_DIR, 'build_log.txt')
with open(log_file, 'w', encoding='utf-8') as f:
    f.write(f"命令: {' '.join(cmd)}\n")
    f.write(f"工作目录: {BASE_DIR}\n\n")
    
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)
    
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write(f"\n=== 返回码: {result.returncode} ===\n")

print(f"\n返回码: {result.returncode}")
print(f"日志已保存到: {log_file}")

if result.returncode != 0:
    print("打包失败，请查看日志文件")
else:
    print("打包成功!")
    dist_path = os.path.join(BASE_DIR, 'dist', 'AI_Trading_System.exe')
    if os.path.exists(dist_path):
        print(f"生成的可执行文件: {dist_path}")
        print(f"文件大小: {os.path.getsize(dist_path) / (1024*1024):.2f} MB")
        print(f"文件时间: {os.path.getmtime(dist_path)}")