# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 打包脚本
使用PyInstaller将Python程序打包成exe文件
"""

import os
import sys
import shutil
from pathlib import Path

# 设置路径（使用原始字符串）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
BUILD_DIR = os.path.join(BASE_DIR, 'build')
SPEC_FILE = os.path.join(BASE_DIR, 'trading_system.spec')

# 清理旧的构建文件
if os.path.exists(DIST_DIR):
    shutil.rmtree(DIST_DIR)
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
if os.path.exists(SPEC_FILE):
    os.remove(SPEC_FILE)

# 生成spec文件内容（使用双反斜杠）
base_dir_escaped = BASE_DIR.replace('\\', '\\\\')

spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['start_gui.py'],
    pathex=['{base_dir_escaped}'],
    binaries=[],
    datas=[
        ('data_cache', 'data_cache'),
        ('portfolio.pkl', '.'),
    ],
    hiddenimports=[
        'akshare',
        'pandas',
        'numpy',
        'tkinter',
        'ttkbootstrap',
        'sqlalchemy',
        'requests',
        'lxml',
        'bs4',
        'matplotlib',
        'scikit-learn',
        'xgboost',
        'lightgbm',
        'catboost',
        'win32com',
        'pywin32',
        'queue',
        'threading',
        'json',
        'hashlib',
        'datetime',
        'time',
        'typing',
        'urllib3',
        'requests.adapters',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI量化交易系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

# 写入spec文件
with open(SPEC_FILE, 'w', encoding='utf-8') as f:
    f.write(spec_content)

print(f"[INFO] 创建spec文件: {SPEC_FILE}")

# 执行打包
import PyInstaller.__main__
PyInstaller.__main__.run([
    SPEC_FILE,
    '--clean',
    '--noconfirm',
])

print(f"[OK] 打包完成！可执行文件位于: {DIST_DIR}")