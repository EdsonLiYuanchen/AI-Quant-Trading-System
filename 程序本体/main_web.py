# -*- coding: utf-8 -*-
"""
AI 量化交易系统 · 统一入口
默认启动 Web 版（HTML/CSS/JS 现代界面）。
带参数 --legacy 时启动旧版 Tkinter 完整界面。
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 打包版(console=False) sys.stdout/stderr 为 None，print 会抛 AttributeError；
# 在导入各业务模块前先兜底，保证冻结后的窗口/服务模式都能正常启动。
try:
    from stream_guard import ensure_streams
    ensure_streams()
except Exception:
    pass


def main():
    if '--legacy' in sys.argv:
        from AI量化交易系统GUI import main as gui_main
        gui_main()
        return
    from AI量化交易系统Web import main as web_main
    web_main()

if __name__ == '__main__':
    main()
