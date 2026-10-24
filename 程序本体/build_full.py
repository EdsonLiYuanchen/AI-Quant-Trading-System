# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

BASE_DIR = os.path.abspath(r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

# 确保数据目录存在
data_cache_dir = os.path.join(BASE_DIR, 'data_cache')
if not os.path.exists(data_cache_dir):
    os.makedirs(data_cache_dir)

# 使用PyInstaller打包，使用列表形式避免PowerShell解析问题
cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    '--console',
    '--onefile',
    '--clean',
    '--name=AI_Trading_System',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    '--hidden-import=encodings',
    '--hidden-import=encodings.utf_8',
    '--hidden-import=encodings.gbk',
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
        
        # 复制必要的数据文件到dist目录
        print("\n复制数据文件到dist目录...")
        dist_data_cache = os.path.join(BASE_DIR, 'dist', 'data_cache')
        if os.path.exists(data_cache_dir):
            if os.path.exists(dist_data_cache):
                shutil.rmtree(dist_data_cache)
            shutil.copytree(data_cache_dir, dist_data_cache)
            print(f"  data_cache 复制成功")
        
        portfolio_src = os.path.join(BASE_DIR, 'portfolio.pkl')
        portfolio_dst = os.path.join(BASE_DIR, 'dist', 'portfolio.pkl')
        if os.path.exists(portfolio_src):
            shutil.copy(portfolio_src, portfolio_dst)
            print(f"  portfolio.pkl 复制成功")
        
        print("\n数据文件复制完成!")