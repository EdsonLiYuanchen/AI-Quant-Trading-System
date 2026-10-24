@echo off
chcp 65001 >nul
cls
echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                                                                            ║
echo ║        🔧 AI量化交易系统 - 完整依赖更新程序                             ║
echo ║                                                                            ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo 📅 更新日期: 2026-04-11
echo 📊 包含: 核心库 + 数据库 + 量化分析 + 技术指标 + 可视化
echo.
echo ⚠️  预计需要 5-10 分钟，请确保网络连接稳定...
echo.
pause

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo [1/8] 更新pip到最新版本...
echo ═══════════════════════════════════════════════════════════════
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo ❌ pip更新失败，尝试使用默认源...
    python -m pip install --upgrade pip
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo [2/8] 安装核心数据处理库...
echo ═══════════════════════════════════════════════════════════════
pip install pandas>=2.0.0 numpy>=1.24.0 scipy>=1.10.0 -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo ⚠️  部分库安装失败，尝试降级版本...
    pip install pandas>=1.5.0 numpy>=1.23.0 scipy>=1.9.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo [3/8] 安装机器学习与量化分析库...
echo ═══════════════════════════════════════════════════════════════
pip install scikit-learn>=1.3.0 xgboost>=1.7.0 lightgbm>=3.3.0 -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo ⚠️  尝试安装兼容版本...
    pip install scikit-learn>=1.1.0 xgboost>=1.5.0 lightgbm>=3.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo [4/8] 安装金融数据接口库...
echo ═══════════════════════════════════════════════════════════════
pip install akshare>=1.12.0 yfinance>=0.2.18 tushare>=1.2.89 efinance>=1.4.2 -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo ⚠️  尝试安装基础版本...
    pip install akshare>=1.10.0 yfinance>=0.2.0 tushare>=1.2.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo [5/8] 安装量化分析与技术指标库...
echo ═══════════════════════════════════════════════════════════════
pip install quantstats>=0.0.62 backtrader>=1.9.78.123 pandas-ta>=0.3.14b0 -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo ⚠️  跳过部分高级库安装...
    pip install quantstats>=0.0.60 -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo [6/8] 安装数据库连接库...
echo ═══════════════════════════════════════════════════════════════
pip install mysql-connector-python>=8.1.0 SQLAlchemy>=2.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo ⚠️  尝试安装兼容版本...
    pip install mysql-connector-python>=8.0.0 SQLAlchemy>=1.4.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo [7/8] 安装数据可视化库...
echo ═══════════════════════════════════════════════════════════════
pip install matplotlib>=3.7.0 seaborn>=0.12.0 plotly>=5.14.0 mplfinance>=0.12.9b7 -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo ⚠️  尝试安装基础可视化库...
    pip install matplotlib>=3.5.0 seaborn>=0.11.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo [8/8] 安装其他工具库...
echo ═══════════════════════════════════════════════════════════════
pip install requests>=2.31.0 openpyxl>=3.1.0 customtkinter>=5.2.0 python-dateutil>=2.8.2 -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                                                                            ║
echo ║                    ✅ 依赖更新完成！                                      ║
echo ║                                                                            ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

REM 验证安装结果
echo 📊 验证已安装的库版本：
echo.
python -c "import pandas as pd; print(f'📈 pandas版本: {pd.__version__}')"
python -c "import numpy as np; print(f'🔢 numpy版本: {np.__version__}')"
python -c "import akshare as ak; print(f'📊 akshare版本: {ak.__version__}')"
python -c "import sklearn; print(f'🤖 scikit-learn版本: {sklearn.__version__}')"
python -c "import quantstats as qs; print(f'📉 quantstats版本: {qs.__version__}')"
python -c "
try:
    import mysql.connector
    print('🗄️  mysql-connector-python: 安装成功')
except:
    print('❌ mysql-connector-python: 安装失败')
"

echo.
echo 📌 接下来请：
echo    [1] 双击运行"启动AI量化交易系统.bat"启动程序
echo    [2] 或运行"python 融合版AI量化交易系统.py"
echo    [3] 如需数据库功能，运行"python database_manager.py"测试连接
echo.
echo ⚠️  如果遇到任何问题，请检查：
echo    - Python版本是否为3.8+
echo    - 网络连接是否正常
echo    - 系统权限是否足够

echo.
echo 按任意键退出...
pause >nul