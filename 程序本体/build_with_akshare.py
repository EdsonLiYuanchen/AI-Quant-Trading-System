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

# 使用PyInstaller打包，添加akshare的file_fold
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
        
        # 复制数据文件到dist目录
        print("\n复制数据文件...")
        dist_dir = os.path.join(BASE_DIR, 'dist')
        
        # 复制data_cache
        src_data_cache = os.path.join(BASE_DIR, 'data_cache')
        dst_data_cache = os.path.join(dist_dir, 'data_cache')
        if os.path.exists(src_data_cache):
            if os.path.exists(dst_data_cache):
                shutil.rmtree(dst_data_cache)
            shutil.copytree(src_data_cache, dst_data_cache)
            print("  data_cache 复制成功")
        
        # 复制portfolio.pkl
        src_portfolio = os.path.join(BASE_DIR, 'portfolio.pkl')
        dst_portfolio = os.path.join(dist_dir, 'portfolio.pkl')
        if os.path.exists(src_portfolio):
            shutil.copy(src_portfolio, dst_portfolio)
            print("  portfolio.pkl 复制成功")