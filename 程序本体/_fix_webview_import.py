# -*- coding: utf-8 -*-
"""Fix the webview import in AI量化交易系统Web.py for PyInstaller."""
import os

web_file = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\AI量化交易系统Web.py'

with open(web_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the sys.path + import webview block
# Line 21 (0-indexed: 20) is: sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Lines 23-28 (0-indexed: 22-27) are the try/except import webview

# Find the exact line numbers
replace_start = None
replace_end = None
for i, line in enumerate(lines):
    if 'sys.path.append(os.path.dirname(os.path.abspath(__file__)))' in line:
        replace_start = i
    if replace_start is not None and line.strip() == 'HAS_WEBVIEW = False':
        replace_end = i
        break

if replace_start is None or replace_end is None:
    print('Could not find the block to replace')
    # Try a different approach - just search for the pattern
    for i, line in enumerate(lines):
        if 'import webview' in line:
            print(f'Found import webview at line {i+1}')
            print(f'Context: {lines[max(0,i-5):i+5]}')
    exit(1)

new_block = [
    'sys.path.append(os.path.dirname(os.path.abspath(__file__)))\n',
    '# PyInstaller: ensure _MEIPASS is on sys.path so bundled webview/akshare can be found\n',
    '_meipass = getattr(sys, "_MEIPASS", None)\n',
    'if _meipass and _meipass not in sys.path:\n',
    '    sys.path.insert(0, _meipass)\n',
    '\n',
    'try:\n',
    '    import webview  # noqa: E402  \xe6\xa1\x8c\xe9\x9d\xa2\xe7\x89\x88\xe7\xaa\x97\xe5\x8f\xa3\xe9\x9c\x80\xe8\xa6\x81\xef\xbc\x8c\xe6\x97\xa0\xe5\xa4\xb4\xe6\x9c\x8d\xe5\x8a\xa1\xe6\xa8\xa1\xe5\xbc\x8f\uff08\xe5\xae\x89\xe8\xa3\x85\uff09\xe4\xb8\x8d\xe4\xbe\x96\xe8\xb5\x96\n',
    '    HAS_WEBVIEW = True\n',
    'except ImportError:\n',
    '    webview = None\n',
    '    HAS_WEBVIEW = False\n',
]

lines[replace_start:replace_end+1] = new_block

with open(web_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'Updated lines {replace_start+1}-{replace_end+1} with _MEIPASS fix')
print('New block:')
for line in new_block:
    print(f'  {line.rstrip()}')
