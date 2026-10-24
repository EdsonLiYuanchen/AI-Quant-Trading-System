# -*- coding: utf-8 -*-
import subprocess
import sys
import os

BASE_DIR = os.path.abspath(r'C:\Users\Edson\code\.vscode\量化交易\程序本体')
LOG_FILE = os.path.join(BASE_DIR, 'pyinstaller_log.txt')

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
    'launcher.py'
]

print(f"工作目录: {BASE_DIR}")
print(f"执行命令: {' '.join(cmd)}")
print(f"日志文件: {LOG_FILE}")

# 运行并保存输出
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(f"命令: {' '.join(cmd)}\n")
    f.write(f"工作目录: {BASE_DIR}\n")
    f.write(f"Python版本: {sys.version}\n")
    f.write("="*80 + "\n\n")
    
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)
    
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write(f"\n=== 返回码: {result.returncode} ===\n")

print(f"\n返回码: {result.returncode}")
print(f"详细日志已保存到: {LOG_FILE}")

# 检查dist目录
dist_dir = os.path.join(BASE_DIR, 'dist')
if os.path.exists(dist_dir):
    items = os.listdir(dist_dir)
    print(f"dist目录内容: {items}")