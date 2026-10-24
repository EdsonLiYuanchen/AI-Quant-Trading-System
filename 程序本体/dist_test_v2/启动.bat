@echo off
chcp 65001 >nul
title AI量化交易系统
echo ========================================
echo   AI量化交易系统
echo ========================================
echo.
echo 正在启动...
echo.

cd /d "%~dp0"
start "" "app\AI_Trading_System.exe"

echo.
echo 程序已启动
pause
