@echo off
chcp 65001 >nul
cls
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║        🔧 AI量化交易系统 - 依赖安装程序                      ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 本程序将自动安装所有必要的Python库
echo 预计需要 3-5 分钟，请耐心等待...
echo.
pause

echo.
echo ═══════════════════════════════════════════════════════════════
echo [1/4] 正在安装核心数据处理库...
echo ═══════════════════════════════════════════════════════════════
pip install pandas numpy scipy scikit-learn -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ═══════════════════════════════════════════════════════════════
echo [2/4] 正在安装金融数据接口库...
echo ═══════════════════════════════════════════════════════════════
pip install akshare yfinance tushare -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ═══════════════════════════════════════════════════════════════
echo [3/4] 正在安装现代化界面库 (可选)...
echo ═══════════════════════════════════════════════════════════════
pip install customtkinter -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ═══════════════════════════════════════════════════════════════
echo [4/4] 正在安装其他工具库...
echo ═══════════════════════════════════════════════════════════════
pip install requests openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║                    ✅ 安装完成！                              ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📌 接下来请：
echo    [1] 双击运行"启动GUI.bat"启动程序
echo    [2] 或运行"python AI量化交易系统GUI.py"
echo.
echo 💡 提示：如果遇到问题，请查看"快速启动指南.txt"
echo.
pause
