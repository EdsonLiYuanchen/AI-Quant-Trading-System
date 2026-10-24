@echo off
chcp 65001 >nul
title AI量化交易系统启动器 (优化版)

echo ========================================
echo   AI量化交易系统GUI启动脚本 (优化版)
echo ========================================
echo.

REM 设置Python路径（可根据实际情况修改）
set PYTHON_CMD=python

REM 检查是否安装了必要的依赖
echo 正在检查依赖项...
%PYTHON_CMD% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到tkinter库，请安装Python GUI支持
    pause
    exit /b 1
)

%PYTHON_CMD% -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo 警告：未找到pandas库，正在尝试安装...
    %PYTHON_CMD% -m pip install pandas
)

%PYTHON_CMD% -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo 警告：未找到numpy库，正在尝试安装...
    %PYTHON_CMD% -m pip install numpy
)

%PYTHON_CMD% -c "import akshare" >nul 2>&1
if errorlevel 1 (
    echo 警告：未找到akshare库，正在尝试安装...
    %PYTHON_CMD% -m pip install akshare
)

%PYTHON_CMD% -c "import matplotlib" >nul 2>&1
if errorlevel 1 (
    echo 警告：未找到matplotlib库，正在尝试安装...
    %PYTHON_CMD% -m pip install matplotlib
)

%PYTHON_CMD% -c "import customtkinter" >nul 2>&1
if errorlevel 1 (
    echo 警告：未找到customtkinter库（可选），正在尝试安装...
    %PYTHON_CMD% -m pip install customtkinter
)

echo.
echo 所有依赖检查完成，正在启动AI量化交易系统...
echo.

REM 启动AI量化交易系统GUI (使用优化的启动器)
cd /d "%~dp0"
%PYTHON_CMD% "start_gui.py"

echo.
echo 程序已退出
pause