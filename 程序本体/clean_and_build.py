# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

BASE_DIR = os.path.abspath(r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

print("=== 彻底清理并重新打包 ===")

# 1. 清理所有旧的构建文件
print("\n1. 清理旧的构建文件...")
for dir_name in ['build', 'dist', '__pycache__']:
    dir_path = os.path.join(BASE_DIR, dir_name)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)
        print(f"   ✓ 删除: {dir_path}")

# 2. 删除旧的spec文件
spec_files = [f for f in os.listdir(BASE_DIR) if f.endswith('.spec')]
for spec_file in spec_files:
    spec_path = os.path.join(BASE_DIR, spec_file)
    os.remove(spec_path)
    print(f"   ✓ 删除: {spec_path}")

# 3. 重新打包
print("\n2. 开始重新打包...")
cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    '--console',
    '--onedir',
    '--clean',
    '--name=AI_Trading_System',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    '--collect-all=akshare',
    '--collect-all=requests',
    '--collect-all=bs4',
    '--collect-all=beautifulsoup4',
    '--hidden-import=增强版数据爬取',
    '--hidden-import=爬取金融数据',
    'launcher.py'
]

print(f"   命令: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=600)

print(f"   返回码: {result.returncode}")

if result.returncode != 0:
    print("\n=== 打包失败 ===")
    print(result.stderr[-3000:])
else:
    print("\n=== 打包成功 ===")
    dist_path = os.path.join(BASE_DIR, 'dist', 'AI_Trading_System', 'AI_Trading_System.exe')
    if os.path.exists(dist_path):
        import time
        mtime = os.path.getmtime(dist_path)
        print(f"   文件: {dist_path}")
        print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
        print(f"   大小: {os.path.getsize(dist_path) / (1024*1024):.2f} MB")
        
        # 复制数据文件
        print("\n3. 复制数据文件...")
        dist_dir = os.path.join(BASE_DIR, 'dist', 'AI_Trading_System')
        
        src_data_cache = os.path.join(BASE_DIR, 'data_cache')
        dst_data_cache = os.path.join(dist_dir, 'data_cache')
        if os.path.exists(src_data_cache):
            if os.path.exists(dst_data_cache):
                shutil.rmtree(dst_data_cache)
            shutil.copytree(src_data_cache, dst_data_cache)
            print(f"   ✓ data_cache 复制成功")
        
        src_portfolio = os.path.join(BASE_DIR, 'portfolio.pkl')
        dst_portfolio = os.path.join(dist_dir, 'portfolio.pkl')
        if os.path.exists(src_portfolio):
            shutil.copy(src_portfolio, dst_portfolio)
            print(f"   ✓ portfolio.pkl 复制成功")
        
        print("\n=== 完成 ===")
        print(f"程序位置: {dist_path}")