# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

BASE_DIR = os.path.abspath(r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

# 清理旧的构建文件
print("清理旧的构建文件...")
for dir_name in ['build', 'dist']:
    dir_path = os.path.join(BASE_DIR, dir_name)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)
        print(f"  已删除: {dir_path}")

# akshare的file_fold目录
akshare_dir = os.path.join(sys.prefix, 'Lib', 'site-packages', 'akshare')
file_fold = os.path.join(akshare_dir, 'file_fold')

print(f"\nakshare目录: {akshare_dir}")
print(f"file_fold目录: {file_fold}")

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
    f'--add-data={file_fold};akshare/file_fold',
    '--collect-all=tkinter',
    '--collect-all=pandas',
    '--collect-all=numpy',
    '--collect-all=akshare',
    '--collect-all=scipy',
    '--collect-all=sqlalchemy',
    '--collect-all=requests',
    '--collect-all=bs4',
    '--collect-all=beautifulsoup4',
    '--hidden-import=增强版数据爬取',
    '--hidden-import=爬取金融数据',
    'launcher.py'
]

print(f"\n工作目录: {BASE_DIR}")
print(f"执行命令: {' '.join(cmd)}")

result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print(f"\n返回码: {result.returncode}")
if result.returncode != 0:
    print("错误输出:")
    print(result.stderr[-5000:] if len(result.stderr) > 5000 else result.stderr)
else:
    print("打包成功!")
    dist_path = os.path.join(BASE_DIR, 'dist', 'AI_Trading_System.exe')
    if os.path.exists(dist_path):
        import time
        mtime = os.path.getmtime(dist_path)
        print(f"文件时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
        print(f"文件大小: {os.path.getsize(dist_path) / (1024*1024):.2f} MB")
        
        # 复制数据文件
        print("\n复制数据文件...")
        dist_dir = os.path.join(BASE_DIR, 'dist')
        
        # 复制data_cache
        src_data_cache = os.path.join(BASE_DIR, 'data_cache')
        dst_data_cache = os.path.join(dist_dir, 'data_cache')
        if os.path.exists(src_data_cache):
            if os.path.exists(dst_data_cache):
                shutil.rmtree(dst_data_cache)
            shutil.copytree(src_data_cache, dst_data_cache)
            print("  ✓ data_cache 复制成功")
        
        # 复制portfolio.pkl
        src_portfolio = os.path.join(BASE_DIR, 'portfolio.pkl')
        dst_portfolio = os.path.join(dist_dir, 'portfolio.pkl')
        if os.path.exists(src_portfolio):
            shutil.copy(src_portfolio, dst_portfolio)
            print("  ✓ portfolio.pkl 复制成功")
        
        print("\n所有文件准备完成!")