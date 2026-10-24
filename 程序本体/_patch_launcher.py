# -*- coding: utf-8 -*-
"""
Patch the launcher to handle the case where webview is not fully available
in the frozen PyInstaller environment. Fall back to server mode.
"""
import os

base = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'
launcher_path = os.path.join(base, 'launcher.py')

new_launcher = '''# -*- coding: utf-8 -*-
import sys
import os

print("=== AI Trading System Launcher ===")
print(f"Python版本: {sys.version}")
print(f"工作目录: {os.getcwd()}")
print(f"脚本目录: {os.path.dirname(__file__)}")

def run_web():
    """Run the Web frontend version."""
    print("正在导入AI量化交易系统Web版...")
    from AI量化交易系统Web import main, HAS_WEBVIEW
    if not HAS_WEBVIEW:
        print("[WARN] pywebview 不可用，使用 --server 无头服务模式")
        sys.argv.append('--server')
        sys.argv.append('--port')
        sys.argv.append('8000')
    main()

def run_gui():
    """Run the tkinter GUI version."""
    print("正在导入AI量化交易系统GUI版...")
    from AI量化交易系统GUI import main
    main()

try:
    sys.path.append(os.path.dirname(__file__))
    print("路径添加成功")
    
    # Try Web version first
    try:
        run_web()
    except (ImportError, ModuleNotFoundError, Exception) as e:
        print(f"Web版启动失败: {e}")
        print("回退到GUI版...")
        try:
            run_gui()
        except Exception as e2:
            print(f"GUI也失败: {e2}")
            import traceback
            traceback.print_exc()
            input("按Enter退出...")
            sys.exit(1)

except Exception as e:
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {e}")
    import traceback
    traceback.print_exc()
    input("按Enter退出...")
    sys.exit(1)
'''

with open(launcher_path, 'w', encoding='utf-8') as f:
    f.write(new_launcher)
print('Updated launcher.py')
print(new_launcher)
