# -*- coding: utf-8 -*-
import subprocess
import sys
import os

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'
LOG_FILE = os.path.join(BASE_DIR, 'pyinstaller_log.txt')

cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--onedir',
    '--name=AI量化交易系统',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    'start_gui.py'
]

with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(f"执行命令: {' '.join(cmd)}\n")
    f.write(f"工作目录: {BASE_DIR}\n")
    f.write("="*60 + "\n\n")
    
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)
    
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write(f"\n=== 返回码: {result.returncode} ===\n")

print(f"打包日志已保存到 {LOG_FILE}")

# 检查dist目录
dist_dir = os.path.join(BASE_DIR, 'dist')
print(f"\n检查dist目录: {dist_dir}")
if os.path.exists(dist_dir):
    items = os.listdir(dist_dir)
    print(f"dist目录内容: {items}")
else:
    print("dist目录不存在")