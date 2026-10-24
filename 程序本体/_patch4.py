# -*- coding: utf-8 -*-
"""补丁：添加 WebView2 运行时到安装程序"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\build_installer.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    print("[3/4] 打包安装程序...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm", "--onefile",
        "--nowindowed", "--windowed",
        "--name=" + APP_NAME + "_安装程序",
        "--add-data=_internal;.",
        "--add-data=install.py;.",
        "--add-data=uninstall.ps1;.",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.filedialog",
        "--exclude-module=win32com",
        os.path.join(src_dir, "install.py"),
    ]'''

new = '''    # 确保 WebView2 运行时在 output_dir 中
    webview_src = os.path.join(dist_dir, "MicrosoftEdgeWebViewRuntimeSetup.exe")
    webview_dst = os.path.join(output_dir, "MicrosoftEdgeWebViewRuntimeSetup.exe")
    if os.path.exists(webview_src) and not os.path.exists(webview_dst):
        shutil.copy2(webview_src, webview_dst)
        print("  已复制 WebView2 运行时安装程序")

    print("[3/4] 打包安装程序...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm", "--onefile",
        "--nowindowed", "--windowed",
        "--name=" + APP_NAME + "_安装程序",
        "--add-data=_internal;.",
        "--add-data=install.py;.",
        "--add-data=uninstall.ps1;.",
        "--add-data=MicrosoftEdgeWebViewRuntimeSetup.exe;.",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.filedialog",
        "--exclude-module=win32com",
        os.path.join(src_dir, "install.py"),
    ]'''

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched OK')
else:
    print('Pattern not found')
    idx = content.find('[3/4] 打包安装程序')
    if idx >= 0:
        print(repr(content[idx:idx+400]))
