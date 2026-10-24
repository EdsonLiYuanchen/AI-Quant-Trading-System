# -*- coding: utf-8 -*-
import subprocess
import sys
import os

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--onedir',
    '--name=AI量化交易系统',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    'start_gui.py'
]

print(f"执行命令: {' '.join(cmd)}")
print(f"工作目录: {BASE_DIR}")
print("="*60)

result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print("\n=== STDOUT ===")
print(result.stdout)
print("\n=== STDERR ===")
print(result.stderr)
print(f"\n=== 返回码: {result.returncode} ===")

# 检查dist目录
dist_dir = os.path.join(BASE_DIR, 'dist')
print(f"\n=== 检查dist目录 {dist_dir} ===")
if os.path.exists(dist_dir):
    items = os.listdir(dist_dir)
    print(f"dist目录内容: {items}")
    for item in items:
        item_path = os.path.join(dist_dir, item)
        if os.path.isdir(item_path):
            print(f"  [目录] {item}")
            sub_items = os.listdir(item_path)[:3]
            print(f"    子目录内容: {sub_items}...")
        else:
            print(f"  [文件] {item}")
else:
    print("dist目录不存在")