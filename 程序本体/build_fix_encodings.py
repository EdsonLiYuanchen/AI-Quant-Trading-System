# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 修复encodings模块问题
"""

import subprocess
import sys
import os
import shutil

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 清理旧文件
print("清理旧的构建文件...")
for dir_name in ['build', 'dist']:
    dir_path = os.path.join(BASE_DIR, dir_name)
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            print(f"  删除: {dir_path}")
        except:
            print(f"  无法删除: {dir_path}")

# 获取akshare的file_fold目录
import akshare
akshare_dir = os.path.dirname(akshare.__file__)
file_fold_dir = os.path.join(akshare_dir, 'file_fold')
print(f"\nakshare file_fold目录: {file_fold_dir}")

# 使用PyInstaller打包，添加更多参数
print("\n开始打包...")
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--noconfirm',
    '--name=AI量化交易系统',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    '--add-binary=' + sys.executable.replace('python.exe', 'python313.dll') + ';.',
    '--hidden-import=encodings',
    '--hidden-import=encodings.utf_8',
    '--hidden-import=encodings.gbk',
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