# -*- coding: utf-8 -*-
"""补丁：修复 build_installer.py 中 install.py 路径问题"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\build_installer.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the line after the first copy loop that ends with the _internal comment
marker = 'print("  已复制: {}".format(fname))'
idx = content.find(marker)
if idx < 0:
    print('Marker not found')
    sys.exit(1)

# Find the end of that statement
end_idx = content.find('\n\n    # 复制 _internal', idx)
if end_idx < 0:
    end_idx = content.find('\n\n    print("[3/4]', idx)

insert_point = end_idx
new_code = '''
    # 同时复制到 output_dir 根目录（PyInstaller --add-data 从 cwd 找文件）
    for fname in ["install.py", "uninstall.ps1"]:
        src = os.path.join(installer_src, fname)
        dst = os.path.join(output_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
'''

if insert_point > 0:
    content = content[:insert_point] + new_code + content[insert_point:]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched: added copy to output_dir root')
else:
    print('Could not find insertion point')
