# -*- coding: utf-8 -*-
import subprocess
import os

# 测试打包后的程序
dist_dir = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\dist'
exe_path = os.path.join(dist_dir, 'AI_Trading_System.exe')

print(f"测试程序: {exe_path}")
print(f"文件存在: {os.path.exists(exe_path)}")

# 运行程序并捕获输出
result = subprocess.run([exe_path], cwd=dist_dir, capture_output=True, timeout=15)

print("\n=== 程序输出 ===")
stdout = result.stdout.decode('utf-8', errors='replace')
print("STDOUT:")
print(stdout)

stderr = result.stderr.decode('utf-8', errors='replace')
print("\nSTDERR:")
print(stderr)

print(f"\n返回码: {result.returncode}")

# 检查是否还有 output_queue 错误
if 'output_queue' in stdout or 'output_queue' in stderr:
    print("\n❌ 错误仍然存在！")
else:
    print("\n✅ 修复成功！没有 output_queue 错误！")