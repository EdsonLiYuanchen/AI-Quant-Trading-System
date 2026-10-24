# -*- coding: utf-8 -*-
"""
AI 量化交易系统 · 统一入口
默认启动 Web 版（HTML/CSS/JS 现代界面）。
带参数 --legacy 时启动旧版 Tkinter 完整界面。
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    if '--legacy' in sys.argv:
        from AI量化交易系统GUI import main as gui_main
        gui_main()
        return
    from AI量化交易系统Web import main as web_main
    web_main()

if __name__ == '__main__':
    main()
