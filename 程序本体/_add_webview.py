# -*- coding: utf-8 -*-
import os, webview, shutil

base = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'
spec_path = os.path.join(base, 'AI_Trading_System.exe.spec')

# Check if webview is in site-packages
src = os.path.dirname(webview.__file__)
print(f'webview source: {src}')

# Copy webview to source dir
dst = os.path.join(base, 'webview')
if not os.path.exists(dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    print(f'Copied webview to source dir')

# Update spec to add webview to hiddenimports and datas
with open(spec_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add 'webview.platforms.edgechromium' to hiddenimports if not there
if 'webview.platforms.edgechromium' not in content:
    content = content.replace(
        "hiddenimports=['tkinter'",
        "hiddenimports=['tkinter', 'webview.platforms.edgechromium', 'webview.platforms.win32', 'webview.platforms.winforms', 'clr', 'pythonnet'"
    )
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated spec with webview hidden imports')
else:
    print('Spec already has webview imports')
