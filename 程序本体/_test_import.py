# -*- coding: utf-8 -*-
import sys, subprocess, os

_MEIPASS = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\dist\AI_Trading_System.exe\_internal'
src_dir = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# Simulate the frozen exe import
code = '''
import sys, os
sys._MEIPASS = r\"C:\\Users\\Edson\\code\\.vscode\\量化交易\\程序本体\\dist\\AI_Trading_System.exe\\_internal\"
sys.path.insert(0, sys._MEIPASS)
print("MEIPASS:", sys._MEIPASS)
print("sys.path[0]:", sys.path[0])
try:
    import webview
    print("webview OK:", webview.__file__)
    from webview.windows import Window
    print("Window OK")
except ImportError as e:
    print("webview FAILED:", e)
    # Check what IS available
    import pkgutil
    import webview as _wv
    print("webview modules:", [m.name for m in pkgutil.iter_modules(_wv.__path__)])
'''

result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr[:300])
