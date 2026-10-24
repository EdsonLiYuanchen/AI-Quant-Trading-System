# -*- coding: utf-8 -*-
import subprocess
import sys

exe_path = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\dist\AI_Trading_System.exe'

print(f"正在运行: {exe_path}")
print("="*60)

try:
    result = subprocess.run(exe_path, capture_output=True, text=True, timeout=30)
    
    print("\n=== STDOUT ===")
    print(result.stdout)
    
    print("\n=== STDERR ===")
    print(result.stderr)
    
    print(f"\n=== 返回码: {result.returncode} ===")
    
except subprocess.TimeoutExpired:
    print("程序超时")
except Exception as e:
    print(f"执行失败: {e}")