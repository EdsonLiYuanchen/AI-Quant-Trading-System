# -*- coding: utf-8 -*-
"""Inject the fixed Web module + webview + akshare into PortableApp, rebuild ZIP, and test."""
import os, shutil, zipfile, webview, akshare, subprocess, time

base = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'
PORTABLE_APP = os.path.join(base, 'PortableApp', 'app')
INTERNAL = os.path.join(PORTABLE_APP, '_internal')
DIST = os.path.join(base, 'dist')
ZIP = os.path.join(DIST, 'AI量化交易系统_便携版.zip')

# 1. Inject webview Python package
src_wv = os.path.dirname(webview.__file__)
dst_wv = os.path.join(INTERNAL, 'webview')
if os.path.exists(dst_wv):
    shutil.rmtree(dst_wv, ignore_errors=True)
shutil.copytree(src_wv, dst_wv, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
print(f'[1] webview injected ({len(os.listdir(dst_wv))} items)')

# 2. Ensure akshare is present
src_ak = os.path.dirname(akshare.__file__)
dst_ak = os.path.join(INTERNAL, 'akshare')
if not os.path.exists(dst_ak):
    shutil.copytree(src_ak, dst_ak, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'tests', 'test_*'))
    print('[2] akshare added')
else:
    print('[2] akshare already exists')

# 3. Update the compiled AI量化交易系统Web.py inside PYZ
# PyInstaller compiles source .py into PYZ archive. We need to overwrite it.
# The simplest approach: copy the fixed source to _internal and let PyInstaller's
# import system pick it up. But PYZ takes priority.
# Alternative: just modify the exe to look for the webview import differently.
# Best approach: rebuild with pyinstaller after fixing the source.

# 4. Copy the fixed Web.py into _internal (as a backup - in case PYZ doesn't shadow it)
web_src = os.path.join(base, 'AI量化交易系统Web.py')
web_dst = os.path.join(INTERNAL, 'AI量化交易系统Web.py')
if os.path.exists(web_src):
    shutil.copy2(web_src, web_dst)
    print('[3] Web module copied to _internal')

# 5. Rebuild ZIP
if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(os.path.join(base, 'PortableApp')):
        for fi in files:
            fp = os.path.join(root, fi)
            arcname = os.path.relpath(fp, os.path.join(base, 'PortableApp'))
            zf.write(fp, arcname)

size = os.path.getsize(ZIP) / 1024 / 1024
print(f'\n[4] ZIP: {size:.1f} MB')

# 6. Test the exe
print('\n[5] Testing exe...')
exe = os.path.join(PORTABLE_APP, 'AI_Trading_System.exe')
proc = subprocess.Popen(
    [exe],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=PORTABLE_APP
)
time.sleep(12)

if proc.poll() is None:
    print('SUCCESS: App is running!')
    proc.kill()
else:
    stdout, stderr = proc.communicate()
    print(f'App exited with code: {proc.returncode}')
    s = stdout.decode('utf-8', errors='replace')
    print(f'STDOUT: {s[-500:]}')
    e = stderr.decode('utf-8', errors='replace')
    if e:
        print(f'STDERR: {e[-300:]}')
