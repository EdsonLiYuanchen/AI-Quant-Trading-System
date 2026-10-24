# -*- coding: utf-8 -*-
import subprocess
import sys
import os

exe_path = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\dist\AI_Trading_System.exe'

print(f"正在运行: {exe_path}")
print(f"文件存在: {os.path.exists(exe_path)}")
if os.path.exists(exe_path):
    print(f"文件大小: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")

print("="*60)

try:
    # 使用不同的编码方式
    result = subprocess.run(exe_path, capture_output=True, text=False, timeout=30)
    
    print("\n=== STDOUT (原始字节) ===")
    try:
        print(result.stdout.decode('utf-8'))
    except:
        try:
            print(result.stdout.decode('gbk'))
        except:
            print(f"无法解码，原始长度: {len(result.stdout)} bytes")
            print(result.stdout[:1000] if len(result.stdout) > 1000 else result.stdout)
    
    print("\n=== STDERR (原始字节) ===")
    try:
        print(result.stderr.decode('utf-8'))
    except:
        try:
            print(result.stderr.decode('gbk'))
        except:
            print(f"无法解码，原始长度: {len(result.stderr)} bytes")
            print(result.stderr[:1000] if len(result.stderr) > 1000 else result.stderr)
    
    print(f"\n=== 返回码: {result.returncode} ===")
    
except subprocess.TimeoutExpired:
    print("程序超时")
except Exception as e:
    print(f"执行失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()