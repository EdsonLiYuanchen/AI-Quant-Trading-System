@echo off
cd /d "%~dp0"
echo 开始打包...
"C:\Users\Edson\AppData\Local\Programs\Python\Python313\python.exe" -m PyInstaller ^
    --console --onefile --clean --name=AI_Trading_System ^
    --add-data=data_cache;data_cache --add-data=smart_cache;smart_cache ^
    --add-data=portfolio.pkl;. --add-data=portfolio.json;. --add-data=watchlist.json;. ^
    --add-data=fund_portfolio.json;. --add-data=fund_portfolio.pkl;. --add-data=fund_records.json;. ^
    --hidden-import=tkinter --hidden-import=tkinter.ttk --hidden-import=tkinter.scrolledtext ^
    --hidden-import=tkinter.messagebox --hidden-import=tkinter.filedialog ^
    --hidden-import=智能数据查询 --hidden-import=长线选股 --hidden-import=自选股 ^
    --hidden-import=同花顺账户导入 --hidden-import=增强版数据爬取 --hidden-import=爬取金融数据 ^
    --hidden-import=多模型AI量化交易 --hidden-import=分析数据 --hidden-import=持仓管理 ^
    --hidden-import=实时行情增强 --hidden-import=tonghuashun_realtime --hidden-import=database_manager ^
    --hidden-import=stream_guard ^
    --hidden-import=mplfinance --hidden-import=matplotlib --hidden-import=matplotlib.backends.backend_tkagg ^
    --hidden-import=matplotlib.backends.backend_agg ^
    --hidden-import=sklearn --hidden-import=sklearn.ensemble --hidden-import=sklearn.model_selection --hidden-import=sklearn.metrics ^
    --hidden-import=scipy --hidden-import=openpyxl --hidden-import=numpy --hidden-import=pandas ^
    launcher.py
echo 打包完成！
dir dist\*.exe