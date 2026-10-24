# -*- coding: utf-8 -*-
import subprocess
import sys
import os

# 使用绝对路径
BASE_DIR = os.path.abspath(r'C:\Users\Edson\code\.vscode\量化交易\程序本体')
LAUNCHER_PATH = os.path.join(BASE_DIR, 'launcher.py')
DATA_CACHE = os.path.join(BASE_DIR, 'data_cache')
PORTFOLIO_FILE = os.path.join(BASE_DIR, 'portfolio.pkl')

print(f"基础目录: {BASE_DIR}")
print(f"启动器路径: {LAUNCHER_PATH}")
print(f"数据缓存: {DATA_CACHE}")

# 使用PyInstaller打包
cmd = [
    sys.executable,
    '-m', 'PyInstaller',
    '--console',
    '--onefile',
    '--clean',
    '--name=AI_Trading_System',
    f'--add-data={DATA_CACHE};data_cache',
    f'--add-data={PORTFOLIO_FILE};.',
    LAUNCHER_PATH
]

print(f"\n执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

print(f"\n返回码: {result.returncode}")
if result.returncode != 0:
    print("STDOUT:", result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout)
    print("STDERR:", result.stderr[-5000:] if len(result.stderr) > 5000 else result.stderr)
else:
    print("打包成功!")
    dist_path = os.path.join(BASE_DIR, 'dist', 'AI_Trading_System.exe')
    if os.path.exists(dist_path):
        print(f"生成的可执行文件: {dist_path}")
        print(f"文件大小: {os.path.getsize(dist_path) / (1024*1024):.2f} MB")