# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('data_cache', 'data_cache'), ('smart_cache', 'smart_cache'), ('portfolio.pkl', '.'), ('portfolio.json', '.'), ('watchlist.json', '.'), ('fund_portfolio.json', '.'), ('fund_portfolio.pkl', '.'), ('fund_records.json', '.'), ('web', 'web'), ('akshare/file_fold', 'akshare/file_fold')],
    hiddenimports=['tkinter', 'webview.platforms.edgechromium', 'webview.platforms.win32', 'webview.platforms.winforms', 'clr', 'pythonnet', 'tkinter.ttk', 'tkinter.scrolledtext', 'tkinter.messagebox', 'tkinter.filedialog', '智能数据查询', '长线选股', '自选股', '同花顺账户导入', '增强版数据爬取', '爬取金融数据', '多模型AI量化交易', '分析数据', '持仓管理', '实时行情增强', 'tonghuashun_realtime', 'database_manager', 'enhanced_database_manager', 'stream_guard', 'ai_strategy', 'AI量化交易系统Web', 'AI量化交易系统GUI', 'headless_server', 'quant_metrics', '全球证券接口预留', 'mplfinance', 'matplotlib', 'matplotlib.backends.backend_tkagg', 'matplotlib.backends.backend_agg', 'sklearn', 'sklearn.ensemble', 'sklearn.model_selection', 'sklearn.metrics', 'scipy', 'openpyxl', 'numpy', 'pandas', 'akshare', 'requests', 'bs4', 'lxml', 'sqlalchemy', 'mysql', 'pymysql', 'webview', 'bottle'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'cv2', 'opencv', 'transformers', 'tokenizers', 'librosa', 'soundfile', '_soundfile_data', 'numba', 'llvmlite', 'imageio_ffmpeg', 'sentencepiece', 'easytrader', 'pywinauto', 'easyutils', 'pythonnet', 'clr', 'comtypes', 'proxy_tools', 'flask', 'werkzeug'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI_Trading_System.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AI_Trading_System.exe',
)
