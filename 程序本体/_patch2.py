# -*- coding: utf-8 -*-
"""补丁：修复文件夹名称"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\build_installer.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = 'dist_dir, "AI_Trading_System", "_internal"'
new = 'dist_dir, "AI_Trading_System.exe", "_internal"'

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed: AI_Trading_System -> AI_Trading_System.exe')
else:
    print('Pattern not found, checking...')
    idx = content.find('_internal')
    if idx >= 0:
        print(repr(content[idx-80:idx+80]))
    else:
        print('_internal not found at all')
