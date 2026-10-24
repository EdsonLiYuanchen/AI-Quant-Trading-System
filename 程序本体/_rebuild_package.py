# -*- coding: utf-8 -*-
import os, shutil, zipfile

base = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'
SRC = os.path.join(base, 'dist', 'test_final')
PORTABLE = os.path.join(base, 'PortableApp')
DIST = os.path.join(base, 'dist')
ZIP = os.path.join(DIST, 'AI量化交易系统_便携版.zip')

if os.path.exists(PORTABLE):
    shutil.rmtree(PORTABLE, ignore_errors=True)
os.makedirs(PORTABLE)
shutil.copytree(os.path.join(SRC, 'app'), os.path.join(PORTABLE, 'app'))
print('Copied app/')

bat = (
    '@echo off\r\n'
    'chcp 65001 >nul\r\n'
    'title AI量化交易系统\r\n'
    'echo ========================================\r\n'
    'echo   AI量化交易系统\r\n'
    'echo ========================================\r\n'
    'echo.\r\n'
    'echo 正在启动...\r\n'
    'echo.\r\n'
    '\r\n'
    'cd /d "%~dp0"\r\n'
    'start "" "app\\AI_Trading_System.exe"\r\n'
    '\r\n'
    'echo.\r\n'
    'echo 程序已启动\r\n'
    'pause\r\n'
)
with open(os.path.join(PORTABLE, '启动.bat'), 'wb') as f:
    f.write(bat.encode('gbk'))

readme = '''========================================
  AI量化交易系统 - 便携版
========================================

使用方法：
1. 解压本文件夹到任意位置（如 D:\AI交易系统）
2. 双击启动.bat运行
3. 首次运行会自动创建数据库

注意：
- 无需安装Python
- 无需安装MySQL
- 无需任何配置
- 可直接删除整个文件夹卸载

系统要求：
- Windows 10/11 (64位)
- 至少500MB可用空间
'''
with open(os.path.join(PORTABLE, '使用说明.txt'), 'w', encoding='utf-8') as f:
    f.write(readme)

if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(PORTABLE):
        for fi in files:
            fp = os.path.join(root, fi)
            arcname = os.path.relpath(fp, PORTABLE)
            zf.write(fp, arcname)

size = os.path.getsize(ZIP) / 1024 / 1024
print(f'ZIP: {size:.1f} MB')

with zipfile.ZipFile(ZIP, 'r') as zf:
    names = zf.namelist()
    top = sorted([n for n in names if n.count('/') == 0])
    exe = [n for n in names if n.endswith('AI_Trading_System.exe')]
    ak = [n for n in names if 'file_fold' in n]
    web = [n for n in names if '/web/' in n]
    wv = [n for n in names if '/webview/' in n]
    print(f'Top: {top}')
    print(f'Exe: {exe}')
    print(f'akshare file_fold: {ak}')
    print(f'web: {web}')
    print(f'webview: {len(wv)} files')
    print(f'Total: {len(names)}')
