# -*- coding: utf-8 -*-
"""重建便携包：复制 dist 产物到 PortableApp，写入启动脚本与说明，打包 ZIP。"""
import os
import shutil
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'dist', 'AI_Trading_System.exe')
PORTABLE = os.path.join(BASE, 'PortableApp')
APP_DST = os.path.join(PORTABLE, 'app')
ZIP_PATH = os.path.join(BASE, 'dist', 'AI量化交易系统_便携版.zip')

# 安全检查：所有删除/覆盖目标必须位于 BASE 之下
for p in (SRC, PORTABLE, APP_DST, ZIP_PATH):
    assert os.path.abspath(p).startswith(os.path.abspath(BASE) + os.sep), p
assert os.path.isdir(SRC), '先运行 pyinstaller 生成 dist/AI_Trading_System.exe'

BAT = '''@echo off
chcp 65001 >nul
title AI量化交易系统
cd /d "%~dp0"
echo 正在启动 AI 量化交易系统，请稍候...
echo.
app\\AI_Trading_System.exe
if errorlevel 1 pause
'''

README = '''========================================
  AI量化交易系统 - 便携版
========================================

使用方法：
1. 将整个文件夹解压到任意位置（如 D:\\AI交易系统）
2. 双击文件夹里的「启动.bat」
3. 稍等几秒，界面会自动弹出（浏览器窗口形式）

环境要求：
- Windows 10 / 11 64位
- 无需安装 Python、MySQL 或任何其它运行库

注意事项：
- 启动后请勿关闭那个黑色的命令行窗口，它是程序本体；
  关闭它程序即停止运行。
- 若界面没有自动弹出，请复制窗口里显示的
  http://127.0.0.1:8899 地址，手动粘贴到浏览器打开。
- 首次启动或首次联网取数会稍慢，属正常现象。
'''

def main():
    if os.path.isdir(APP_DST):
        shutil.rmtree(APP_DST)
    os.makedirs(PORTABLE, exist_ok=True)
    shutil.copytree(SRC, APP_DST)
    print('[1] 已复制程序文件到 PortableApp/app')

    with open(os.path.join(PORTABLE, '启动.bat'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(BAT)
    with open(os.path.join(PORTABLE, '使用说明.txt'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(README)
    print('[2] 已写入 启动.bat / 使用说明.txt')

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(PORTABLE):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for fi in files:
                fp = os.path.join(root, fi)
                arc = os.path.join('AI量化交易系统_便携版',
                                   os.path.relpath(fp, PORTABLE))
                zf.write(fp, arc)
    size = os.path.getsize(ZIP_PATH) / 1024 / 1024
    print('[3] ZIP 完成: %s (%.1f MB)' % (ZIP_PATH, size))


if __name__ == '__main__':
    main()
