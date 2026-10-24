# -*- coding: utf-8 -*-
import subprocess
import sys
import os

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 使用PyInstaller打包，避免PowerShell解析问题
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--noconfirm',
    '--name=AI量化交易系统',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    'simple_launcher.py'
]

print(f"开始打包，命令: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print(f"\n返回码: {result.returncode}")
if result.returncode != 0:
    print("STDOUT:", result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout)
    print("STDERR:", result.stderr[-5000:] if len(result.stderr) > 5000 else result.stderr)
else:
    print("打包成功!")
    # 检查dist目录
    dist_dir = os.path.join(BASE_DIR, 'dist')
    if os.path.exists(dist_dir):
        items = os.listdir(dist_dir)
        print(f"dist目录内容: {items}")