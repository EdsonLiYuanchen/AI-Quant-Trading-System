# -*- coding: utf-8 -*-
"""Inject webview + akshare into the PortableApp exe's _internal dir."""
import os, shutil, webview, akshare

base = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'
PORTABLE_APP = os.path.join(base, 'PortableApp', 'app')
INTERNAL = os.path.join(PORTABLE_APP, '_internal')

# 1. Copy the full webview Python package
src_wv = os.path.dirname(webview.__file__)
dst_wv = os.path.join(INTERNAL, 'webview')
if os.path.exists(dst_wv):
    shutil.rmtree(dst_wv, ignore_errors=True)
shutil.copytree(src_wv, dst_wv, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
print(f'webview: {len(os.listdir(dst_wv))} items')
print(f'  platforms: {sorted(os.listdir(os.path.join(dst_wv, "platforms"))) if os.path.exists(os.path.join(dst_wv, "platforms")) else "MISSING"}')

# 2. Ensure akshare is complete
src_ak = os.path.dirname(akshare.__file__)
dst_ak = os.path.join(INTERNAL, 'akshare')
if not os.path.exists(dst_ak):
    shutil.copytree(src_ak, dst_ak, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'tests', 'test_*'))
    print('akshare added')
else:
    print('akshare already exists')
print(f'  file_fold: {os.path.exists(os.path.join(dst_ak, "file_fold"))}')

# 3. Verify web dir
web_dir = os.path.join(INTERNAL, 'web')
print(f'web: {os.path.exists(web_dir)}')
if os.path.exists(web_dir):
    print(f'  contents: {os.listdir(web_dir)}')

# 4. Final size check
exe = os.path.join(PORTABLE_APP, 'AI_Trading_System.exe')
total = 0
for root, dirs, files in os.walk(PORTABLE_APP):
    for f in files:
        total += os.path.getsize(os.path.join(root, f))
print(f'\nTotal app size: {total/1024/1024:.1f} MB')
