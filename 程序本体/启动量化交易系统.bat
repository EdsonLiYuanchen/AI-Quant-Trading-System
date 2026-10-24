@echo off
chcp 65001 >nul
title AI量化交易系统 v2.0

echo ================================
echo     AI量化交易系统
echo ================================
echo.

set "SCRIPT_DIR=%~dp0"
set "LAUNCHER=start_gui.py"

cd /d "%SCRIPT_DIR%"

echo 当前目录: %cd%
echo.

echo 正在启动程序...
echo -------------------------------

python "%LAUNCHER%"

echo.
echo 程序已退出
pause
