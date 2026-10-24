# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 使用完整路径打包
"""

import subprocess
import sys
import os
import shutil

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 检查Python安装
print("检查Python安装...")
print(f"Python路径: {sys.executable}")
print(f"Python版本: {sys.version}")

# 获取akshare的file_fold目录
import akshare
akshare_dir = os.path.dirname(akshare.__file__)
file_fold_dir = os.path.join(akshare_dir, 'file_fold')

# 使用完整的PyInstaller命令
print("\n开始打包...")
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--noconfirm',
    '--name=AI量化交易系统',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    '--paths=' + os.path.dirname(sys.executable) + '\\Lib',
    '--paths=' + os.path.dirname(sys.executable) + '\\Lib\\site-packages',
    'start_gui.py'
]

print(f"执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print("\n=== 打包结果 ===")
print(f"返回码: {result.returncode}")
if result.returncode != 0:
    print("STDOUT:", result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
    print("STDERR:", result.stderr[-3000:] if len(result.stderr) > 3000 else result.stderr)
else:
    print("打包成功!")
    
    # 复制akshare数据文件
    dist_dir = os.path.join(BASE_DIR, 'dist', 'AI量化交易系统')
    dest_akshare = os.path.join(dist_dir, 'akshare', 'file_fold')
    
    if os.path.exists(dest_akshare):
        shutil.rmtree(dest_akshare)
    
    shutil.copytree(file_fold_dir, dest_akshare)
    print(f"akshare数据复制成功")