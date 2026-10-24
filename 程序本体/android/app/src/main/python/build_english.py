# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 清理旧文件
print("Cleaning old build files...")
for item in ['build', 'dist', 'AI_Trading_System.spec']:
    path = os.path.join(BASE_DIR, item)
    if os.path.exists(path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"  Removed: {path}")
        except:
            pass

# 使用英文名称打包
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--clean',
    '--name=AI_Trading_System',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    'launcher.py'
]

print(f"\nRunning command: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print(f"\nReturn code: {result.returncode}")
if result.returncode != 0:
    print("STDOUT:", result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout)
    print("STDERR:", result.stderr[-5000:] if len(result.stderr) > 5000 else result.stderr)
else:
    print("Build successful!")
    dist_dir = os.path.join(BASE_DIR, 'dist')
    if os.path.exists(dist_dir):
        items = os.listdir(dist_dir)
        print(f"dist contents: {items}")