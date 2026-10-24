# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import time

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 测试PyInstaller是否能正常工作
test_cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--version'
]

print("测试PyInstaller版本...")
result = subprocess.run(test_cmd, capture_output=True, text=True)
print(f"PyInstaller版本: {result.stdout.strip()}")

# 测试简单脚本
print("\n测试简单脚本打包...")
simple_script = os.path.join(BASE_DIR, 'test_simple3.py')
with open(simple_script, 'w') as f:
    f.write('print("Hello World")\n')

test_build_cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--clean',
    '--name=test_simple3',
    simple_script
]

print(f"命令: {' '.join(test_build_cmd)}")
result = subprocess.run(test_build_cmd, cwd=BASE_DIR, capture_output=True, text=True)

print(f"\n返回码: {result.returncode}")
if result.stdout:
    print("STDOUT:", result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)

# 检查结果
dist_dir = os.path.join(BASE_DIR, 'dist')
if os.path.exists(dist_dir):
    items = os.listdir(dist_dir)
    print(f"\ndist目录内容: {items}")
else:
    print("\ndist目录不存在")

# 清理测试文件
if os.path.exists(simple_script):
    os.remove(simple_script)