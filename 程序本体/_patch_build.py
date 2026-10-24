# -*- coding: utf-8 -*-
"""补丁脚本：修复 build_installer.py 中缺少 _internal 复制的问题"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\build_installer.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '    print("[3/4] 打包安装程序...")'
new = '''    # 复制 _internal 文件夹到输出目录（PyInstaller 需要它在这里）
    internal_src = os.path.join(dist_dir, "AI_Trading_System", "_internal")
    internal_dst = os.path.join(output_dir, "_internal")
    if os.path.exists(internal_src):
        if os.path.exists(internal_dst):
            shutil.rmtree(internal_dst, ignore_errors=True)
        shutil.copytree(internal_src, internal_dst)
        from pathlib import Path as _P
        sz = sum(f.stat().st_size for f in _P(internal_src).rglob("*") if f.is_file())
        print("  已复制 _internal ({:.1f} MB)".format(sz / 1024 / 1024))
    else:
        print("  警告: _internal 不存在于 {}".format(internal_src))

    print("[3/4] 打包安装程序...")'''

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched OK")
else:
    print("Pattern not found")
    idx = content.find('[3/4] 打包')
    print(repr(content[idx-20:idx+80]))
