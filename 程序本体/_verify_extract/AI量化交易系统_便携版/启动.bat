@echo off
chcp 65001 >nul
title AI量化交易系统
cd /d "%~dp0"
echo 正在启动 AI 量化交易系统，请稍候...
echo.
app\AI_Trading_System.exe
if errorlevel 1 pause
