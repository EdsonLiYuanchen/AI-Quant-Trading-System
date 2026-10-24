# -*- coding: utf-8 -*-
import subprocess
import sys
import os

BASE_DIR = os.path.abspath(r'C:\Users\Edson\code\.vscode\量化交易\程序本体')

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
    '--collect-all=akshare',
    '--collect-all=requests',
    '--collect-all=bs4',
    '--collect-all=beautifulsoup4',
    '--hidden-import=增强版数据爬取',
    '--hidden-import=爬取金融数据',
    'launcher.py',
    '--log-level=DEBUG'
]

print(f"执行命令: {' '.join(cmd)}")
print(f"工作目录: {BASE_DIR}")

# 运行并捕获所有输出
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=600)

print(f"\n返回码: {result.returncode}")

# 保存日志文件
log_file = os.path.join(BASE_DIR, 'pyinstaller_full_log.txt')
with open(log_file, 'w', encoding='utf-8') as f:
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)

print(f"日志已保存到: {log_file}")

if result.returncode != 0:
    print("\n=== 错误输出 (最后3000字符) ===")
    print(result.stderr[-3000:] if len(result.stderr) > 3000 else result.stderr)
else:
    print("\n打包成功!")
    dist_path = os.path.join(BASE_DIR, 'dist', 'AI_Trading_System.exe')
    if os.path.exists(dist_path):
        import time
        mtime = os.path.getmtime(dist_path)
        print(f"文件时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
        print(f"文件大小: {os.path.getsize(dist_path) / (1024*1024):.2f} MB")