# -*- coding: utf-8 -*-
"""便携版启动器：优先桌面窗口（pywebview），不可用时回退本地浏览器界面，
最后回退 tkinter 老界面。"""
import os
import sys

print('=== AI 量化交易系统 启动中 ===')
print('Python: %s' % sys.version)
print('工作目录: %s' % os.getcwd())

# PyInstaller onedir: _MEIPASS 指向 _internal，需要放到 sys.path 最前面
_MEIPASS = getattr(sys, '_MEIPASS', None)
if _MEIPASS:
    print('_MEIPASS: %s' % _MEIPASS)
    if _MEIPASS not in sys.path:
        sys.path.insert(0, _MEIPASS)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.append(_HERE)


def run_web():
    print('正在加载 Web 界面...')
    from AI量化交易系统Web import main
    main()


def run_gui():
    print('正在加载经典界面...')
    from AI量化交易系统GUI import main as gui_main
    gui_main()


def _show_error(exc):
    print('启动失败: %s' % exc)
    import traceback
    traceback.print_exc()


def main():
    try:
        run_web()
        return
    except Exception as e:
        _show_error(e)
    print('尝试回退到经典界面...')
    try:
        run_gui()
        return
    except Exception as e2:
        _show_error(e2)
    try:
        input('按回车键退出...')
    except Exception:
        pass
    sys.exit(1)


if __name__ == '__main__':
    main()
