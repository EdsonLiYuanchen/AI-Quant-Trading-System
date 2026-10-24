# -*- coding: utf-8 -*-
import subprocess
import os
import sys

# 测试打包后的程序
dist_dir = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\dist'
exe_path = os.path.join(dist_dir, 'AI_Trading_System.exe')

# 检查文件是否存在
if not os.path.exists(exe_path):
    print(f"错误: {exe_path} 不存在")
    exit(1)

print(f"测试程序: {exe_path}")
print(f"文件时间: {os.path.getmtime(exe_path)}")

# 运行程序并捕获输出
try:
    result = subprocess.run([exe_path], cwd=dist_dir, capture_output=True, timeout=15)
    
    print("\n=== STDOUT ===")
    stdout = result.stdout.decode('utf-8', errors='replace')
    print(stdout)
    
    print("\n=== STDERR ===")
    stderr = result.stderr.decode('utf-8', errors='replace')
    print(stderr)
    
    print(f"\n返回码: {result.returncode}")
    
except subprocess.TimeoutExpired:
    print("程序运行超时（可能正在运行GUI）")
except Exception as e:
    print(f"执行出错: {e}")