# -*- coding: utf-8 -*-
"""Final fix: inject correct Web module + webview into test_final build, copy to PortableApp, rebuild ZIP."""
import os, shutil, zipfile, webview, akshare

base = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'
SRC_APP = os.path.join(base, 'dist', 'test_final', 'app')
PORTABLE_APP = os.path.join(base, 'PortableApp', 'app')
PORTABLE = os.path.join(base, 'PortableApp')
DIST = os.path.join(base, 'dist')
ZIP = os.path.join(DIST, 'AI量化交易系统_便携版.zip')
INTERNAL = os.path.join(SRC_APP, '_internal')

# 1. Inject webview Python package into _internal
src_wv = os.path.dirname(webview.__file__)
dst_wv = os.path.join(INTERNAL, 'webview')
if os.path.exists(dst_wv):
    shutil.rmtree(dst_wv, ignore_errors=True)
shutil.copytree(src_wv, dst_wv, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
print(f'[1] webview injected into test_final/_internal')

# 2. Ensure akshare
src_ak = os.path.dirname(akshare.__file__)
dst_ak = os.path.join(INTERNAL, 'akshare')
if not os.path.exists(dst_ak):
    shutil.copytree(src_ak, dst_ak, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'tests', 'test_*'))
    print('[2] akshare added')
else:
    print('[2] akshare already exists')

# 3. Copy updated source files to _internal so they override PYZ
# Copy the fixed Web module
web_src = os.path.join(base, 'AI量化交易系统Web.py')
web_dst = os.path.join(INTERNAL, 'AI量化交易系统Web.py')
if os.path.exists(web_src):
    shutil.copy2(web_src, web_dst)
    print('[3] AI量化交易系统Web.py copied to _internal')

# Copy the fixed launcher
launcher_src = os.path.join(base, 'launcher.py')
launcher_dst = os.path.join(INTERNAL, 'launcher.py')
if os.path.exists(launcher_src):
    shutil.copy2(launcher_src, launcher_dst)
    print('[4] launcher.py copied to _internal')

# 4. Rebuild PortableApp from test_final
if os.path.exists(PORTABLE_APP):
    shutil.rmtree(PORTABLE_APP, ignore_errors=True)
shutil.copytree(SRC_APP, PORTABLE_APP)
print(f'[5] PortableApp/app updated ({os.path.getsize(os.path.join(PORTABLE_APP, "AI_Trading_System.exe"))/1024/1024:.1f} MB)')

# 5. Create launcher bat
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

# 6. Create readme
readme = '''========================================
  AI量化交易系统 - 便携版
========================================

使用方法：
1. 解压到任意位置（如 D:\\AI交易系统）
2. 双击 启动.bat 运行
3. 无需安装 Python / MySQL

系统要求：Windows 10/11 64位
'''
with open(os.path.join(PORTABLE, '使用说明.txt'), 'w', encoding='utf-8') as f:
    f.write(readme)

# 7. Rebuild ZIP
if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(PORTABLE):
        for fi in files:
            fp = os.path.join(root, fi)
            arcname = os.path.relpath(fp, PORTABLE)
            zf.write(fp, arcname)

size = os.path.getsize(ZIP) / 1024 / 1024
print(f'[6] ZIP: {size:.1f} MB')

# 8. Verify ZIP contents
with zipfile.ZipFile(ZIP, 'r') as zf:
    names = zf.namelist()
    wv = [n for n in names if '/webview/' in n]
    ak = [n for n in names if 'file_fold' in n]
    web = [n for n in names if '/web/' in n]
    exe = [n for n in names if n.endswith('AI_Trading_System.exe')]
    print(f'  exe: {exe}')
    print(f'  web: {web}')
    print(f'  akshare file_fold: {ak}')
    print(f'  webview: {len(wv)} files')
    print(f'  total: {len(names)} files')
