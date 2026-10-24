# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 打包脚本（不清理旧文件）
"""

import subprocess
import sys
import os
import shutil

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'
DIST_DIR = os.path.join(BASE_DIR, 'dist')

# 获取akshare的file_fold目录
import akshare
akshare_dir = os.path.dirname(akshare.__file__)
file_fold_dir = os.path.join(akshare_dir, 'file_fold')
print(f"akshare file_fold目录: {file_fold_dir}")

# 使用PyInstaller单文件模式打包（带控制台）
print("\n开始打包...")
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--noconfirm',
    '--name=AI量化交易系统',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
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
    
    # 复制akshare数据文件到dist目录
    print("\n复制akshare数据文件...")
    dest_akshare = os.path.join(DIST_DIR, 'akshare')
    dest_file_fold = os.path.join(dest_akshare, 'file_fold')
    
    if os.path.exists(dest_file_fold):
        shutil.rmtree(dest_file_fold)
    
    shutil.copytree(file_fold_dir, dest_file_fold)
    print(f"  复制成功: {file_fold_dir} -> {dest_file_fold}")
    
    # 检查结果
    print("\n=== 打包结果检查 ===")
    exe_path = os.path.join(DIST_DIR, 'AI量化交易系统.exe')
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"  可执行文件: {exe_path}")
        print(f"  文件大小: {size:.2f} MB")
        
        if os.path.exists(dest_file_fold):
            files = os.listdir(dest_file_fold)
            print(f"  akshare数据文件: {len(files)} 个")
        else:
            print("  akshare数据文件复制失败")
    else:
        print("  可执行文件未生成")