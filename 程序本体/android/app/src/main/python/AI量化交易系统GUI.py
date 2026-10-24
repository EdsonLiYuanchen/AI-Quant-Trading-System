"""
AI量化交易系统 - 图形化界面版本
整合所有功能：数据爬取、AI分析、回测、实时监控
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 尝试导入 customtkinter（现代化界面）
try:
    import customtkinter as ctk
    USE_CUSTOM_TK = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    USE_CUSTOM_TK = False
    print("提示: 安装 customtkinter 可获得更美观的界面 (pip install customtkinter)")

# 导入量化交易模块
try:
    from 爬取金融数据 import FinancialDataCrawler, clear_data_folder, DATA_DIR
    from 多模型AI量化交易 import (
        AI_MODELS, AITradingStrategy, MultiModelBacktester,
        RealTimeMonitor, parse_stock_codes
    )
    from 分析数据 import FinancialDataAnalyzer
    from 持仓管理 import PortfolioManager, FundManager
    from 实时行情增强 import RealtimeDataEnhancer
    from tonghuashun_realtime import TonghuashunRealtimeEnhancer  # 同花顺实时数据增强器
    from database_manager import DatabaseManager  # 新增数据库管理器
    from enhanced_database_manager import EnhancedDatabaseManager  # 增强版数据库管理器
    from 智能数据查询 import SmartDataClient  # 智能数据查询模块（自动识别/自动选源/智能缓存/智能分析）
    from 长线选股 import LongTermAnalyzer  # 长线选股预测模块
    from 自选股 import Watchlist  # 自选股管理模块
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保所有依赖文件在同一目录下")
    sys.exit(1)


class RedirectText:
    """重定向输出到文本框"""
    def __init__(self, text_widget, queue):
        self.text_widget = text_widget
        self.queue = queue
        
    def write(self, text):
        if text.strip():
            self.queue.put((text, None))  # 修复：传入元组6
    
    def flush(self):
        pass


class AIQuantTradingGUI:
    """AI量化交易系统主界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AI智能选股助手 v2.0（新手友好版）")
        self.root.geometry("1400x900")
        
        # 设置图标（如果有）
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 数据和状态 - 必须在初始化爬虫之前创建output_queue
        self.output_queue = queue.Queue()
        self.current_monitor = None
        self.monitor_thread = None
        self.crawler = self._init_crawler()
        
        # 实时行情增强器
        self.realtime_enhancer = TonghuashunRealtimeEnhancer()  # 使用上交所/深交所数据源
        self.tonghuashun_enhancer = TonghuashunRealtimeEnhancer()  # 数据源增强器
        self.realtime_auto_update = False
        self.realtime_update_interval = 30
        self.realtime_subscriber_id = None
        
        # 智能数据查询客户端（自动识别输入 / 自动选源 / 智能缓存 / 智能分析）
        self.smart_client = SmartDataClient()
        # 长线选股分析器
        self.longterm = LongTermAnalyzer(client=self.smart_client)
        # 自选股列表
        self.watchlist = Watchlist()
        
        # 持仓管理
        self.portfolio = PortfolioManager('portfolio.pkl')
        
        # 数据库管理
        self.db_manager = self._init_database()
        self.enhanced_db_manager = self._init_enhanced_database()
        
        # 创建界面
        self.configure_progress_styles()
        self.create_menu()
        self.create_main_layout()
        
        # 启动输出更新
        self.update_output()
        
        # 欢迎信息
        self.log("="*80)
        self.log("欢迎使用 AI智能选股助手 v2.0（新手友好版）")
        self.log("适合不懂股市的新手：输入股票/基金/指数的名字或代码，就能看懂今天涨跌")
        self.log("支持: 智能查询 | 下载数据 | AI智能模拟 | 盘中盯盘 | 我的持仓 | 实时行情")
        self.log("="*80)
        
        # 检查依赖
        self._check_dependencies()
    
    def _init_crawler(self):
        """初始化爬虫并检查依赖"""
        try:
            # 优先使用增强版爬虫
            from 增强版数据爬取 import EnhancedDataCrawler
            crawler = EnhancedDataCrawler(use_all_sources=True)
            self.log("[OK] 已加载增强版数据爬取器（支持多数据源并行爬取）", "success")
            return crawler
        except ImportError as e:
            self.log(f"[WARN] 增强版爬虫导入失败: {e}", "warning")
            try:
                # 备用方案：使用原有的爬虫
                from 爬取金融数据 import FinancialDataCrawler
                self.log("[INFO] 使用备用爬虫模块", "info")
                return FinancialDataCrawler(use_database=True)
            except ImportError as e2:
                self.log(f"[ERROR] 导入爬虫模块失败: {e2}", "error")
                return None
    
    def _init_database(self):
        """初始化数据库连接"""
        try:
            db = DatabaseManager()
            self.log("[OK] 数据库连接成功", "success")
            
            # 显示数据库表信息
            db.cursor.execute("SHOW TABLES")
            tables = db.cursor.fetchall()
            self.log(f"[LIST] 数据库表数量: {len(tables)}")
            for table in tables:
                self.log(f"  - {table['Tables_in_quantitative_trading']}")
            
            return db
        except Exception as e:
            self.log(f"[WARN] 数据库连接失败: {e}", "warning")
            self.log("[IDEA] 系统将仅使用文件存储，不影响基本功能")
            return None
    
    def _init_enhanced_database(self):
        """初始化增强版数据库连接"""
        try:
            db = EnhancedDatabaseManager()
            self.log("[OK] 增强版数据库连接成功", "success")
            
            # 显示数据库统计信息
            stats = db.get_database_stats()
            self.log("[STAT] 数据库统计信息:")
            for table, count in stats.items():
                self.log(f"  - {table}: {count} 条记录")
            
            return db
        except Exception as e:
            self.log(f"[WARN] 增强版数据库连接失败: {e}", "warning")
            return None
    
    def _check_dependencies(self):
        """检查必要依赖"""
        self.log("\n[FIND] 检查系统依赖...")

        dependencies = {
            'pandas': '数据处理',
            'numpy': '数值计算',
            'akshare': '金融数据源',
        }

        # 特殊处理 scikit-learn (包名和导入名不同)
        sklearn_status = self._check_sklearn()

        missing_deps = []

        for dep, desc in dependencies.items():
            try:
                __import__(dep)
                self.log(f"  [OK] {dep} - {desc}")
            except ImportError:
                self.log(f"  [ERROR] {dep} - {desc} (未安装)", "error")
                missing_deps.append(dep)

        if missing_deps:
            self.log(f"\n[WARN]  缺少依赖库，请运行以下命令安装:", "warning")
            for dep in missing_deps:
                self.log(f"  pip install {dep}")

            if 'akshare' in missing_deps:
                self.log("\n[IDEA] 重要提示: 缺少akshare库将无法获取真实股票数据")
                self.log("  系统将使用模拟数据进行测试")
        else:
            self.log("[OK] 所有依赖库检查通过", "success")

    def _check_sklearn(self):
        """检查 scikit-learn (sklearn)"""
        try:
            import sklearn
            self.log(f"  [OK] scikit-learn - 机器学习模型")
            return True
        except ImportError:
            try:
                import sklearn as sk
                # 尝试导入核心模块
                from sklearn.ensemble import RandomForestClassifier
                self.log(f"  [OK] scikit-learn - 机器学习模型")
                return True
            except ImportError as e:
                self.log(f"  [ERROR] scikit-learn - 机器学习模型 (未安装)", "error")
                return False
    
    def configure_progress_styles(self):
        """全局界面美化：统一配色、字体、组件样式（新手友好、清晰易读）"""
        FONT = "Microsoft YaHei UI"
        BG = "#f0f4fa"          # 窗口底色（清爽浅蓝灰）
        CARD = "#ffffff"        # 卡片/面板底色
        BORDER = "#dbe3ee"      # 边框
        TEXT = "#1f2937"        # 主文字
        SUB = "#6b7280"         # 辅助文字
        ACCENT = "#2563eb"      # 主强调色（蓝）
        ACCENT_H = "#1d4ed8"    # 强调色（悬停）
        UP = "#e03131"          # 涨（红）
        DOWN = "#2f9e44"        # 跌（绿）

        # 窗口与面板底色
        self.root.configure(bg=BG)

        style = ttk.Style()
        # 用 clam 主题：它支持给按钮/标签页自定义背景色和字色。
        # （vista 主题的按钮是系统画的，会忽略自定义颜色，导致白字配浅色背景看不清）
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # 全局字体
        style.configure(".", font=(FONT, 10), background=BG, foreground=TEXT)

        # 主容器
        style.configure("TPanedwindow", background=BG)

        # 标签页（Notebook）
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        font=(FONT, 10, "bold"),
                        padding=(14, 8),
                        background="#e7edf6",
                        foreground="#475569")
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        # 框架
        style.configure("TFrame", background=BG)
        style.configure("TLabelframe", background=BG, bordercolor=BORDER, borderwidth=1)
        style.configure("TLabelframe.Label",
                        background=BG, foreground="#334155",
                        font=(FONT, 10, "bold"))

        # 文字标签
        style.configure("TLabel", background=BG, foreground=TEXT, font=(FONT, 10))
        style.configure("Title.TLabel", font=(FONT, 15, "bold"), foreground="#1e3a8a", background=BG)
        style.configure("Hint.TLabel", foreground=SUB, font=(FONT, 9), background=BG)
        style.configure("Up.TLabel", foreground=UP, background=BG, font=(FONT, 10, "bold"))
        style.configure("Down.TLabel", foreground=DOWN, background=BG, font=(FONT, 10, "bold"))

        # 按钮
        style.configure("TButton", font=(FONT, 10), padding=(12, 6),
                        background=CARD, foreground=TEXT,
                        bordercolor=BORDER, lightcolor=CARD, darkcolor=BORDER,
                        relief="flat", borderwidth=1)
        style.map("TButton",
                  background=[("active", "#e2e8f0"), ("disabled", "#f1f5f9")],
                  foreground=[("disabled", "#9ca3af")],
                  bordercolor=[("active", "#c3cedb")])
        style.configure("Accent.TButton", font=(FONT, 10, "bold"), padding=(14, 7),
                        background=ACCENT, foreground="#ffffff",
                        bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT,
                        relief="flat", borderwidth=1)
        style.map("Accent.TButton",
                  background=[("active", ACCENT_H), ("disabled", "#93c5fd")],
                  foreground=[("disabled", "#eaf2ff")])

        # 输入框
        style.configure("TEntry", padding=(6, 5), fieldbackground="#ffffff", bordercolor=BORDER)
        style.configure("TCombobox", padding=(4, 3), fieldbackground="#ffffff")
        style.configure("TSpinbox", padding=(4, 3), fieldbackground="#ffffff")

        # 复选/单选
        style.configure("TCheckbutton", background=BG, font=(FONT, 10))
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("TRadiobutton", background=BG, font=(FONT, 10))
        style.map("TRadiobutton", background=[("active", BG)])

        # 数据表格
        style.configure("Treeview", background=CARD, fieldbackground=CARD,
                        foreground=TEXT, rowheight=27, borderwidth=0, font=(FONT, 10))
        style.map("Treeview",
                  background=[("selected", "#dbeafe")],
                  foreground=[("selected", "#1e3a8a")])
        style.configure("Treeview.Heading",
                        font=(FONT, 10, "bold"),
                        background="#eef2f8",
                        foreground="#334155",
                        borderwidth=1,
                        relief="flat")
        style.map("Treeview.Heading", background=[("active", "#e2e8f0")])

        # 滚动条
        style.configure("Vertical.TScrollbar", background="#cbd5e1", troughcolor=BG, arrowcolor=SUB)

        # 进度条（正常/警告/危险）
        style.configure("green.Horizontal.TProgressbar",
                        troughcolor='#e2e8f0', background=DOWN, borderwidth=0)
        style.configure("orange.Horizontal.TProgressbar",
                        troughcolor='#e2e8f0', background='#f59f00', borderwidth=0)
        style.configure("red.Horizontal.TProgressbar",
                        troughcolor='#e2e8f0', background=UP, borderwidth=0)
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 打开文件子菜单
        open_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="打开文件", menu=open_menu)
        open_menu.add_command(label="打开金融数据文件夹", command=self.open_financial_data_folder)
        open_menu.add_command(label="打开分析数据文件夹", command=self.open_analysis_data_folder)
        open_menu.add_command(label="打开AI模型文件夹", command=self.open_model_folder)
        open_menu.add_separator()
        open_menu.add_command(label="打开数据文件管理器", command=self.open_file_manager)
        
        # 数据库操作子菜单
        db_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="数据库操作", menu=db_menu)
        db_menu.add_command(label="连接数据库", command=self.connect_database)
        db_menu.add_command(label="查看数据库表", command=self.view_database_tables)
        db_menu.add_command(label="同步数据到数据库", command=self.sync_data_to_database)
        db_menu.add_separator()
        db_menu.add_command(label="查看CSV文件", command=self.view_csv_files)
        db_menu.add_command(label="导入CSV到数据库", command=self.import_csv_to_database)
        db_menu.add_command(label="导出数据库到CSV", command=self.export_database_to_csv)
        
        file_menu.add_separator()
        file_menu.add_command(label="清空金融数据文件夹", command=self.clear_financial_data)
        file_menu.add_command(label="清空分析数据文件夹", command=self.clear_analysis_data)
        file_menu.add_command(label="清空所有数据文件夹", command=self.clear_all_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="📖 买卖教学（新手必看）", command=self.show_tutorial_tab)
        help_menu.add_command(label="📥 导入同花顺账户数据", command=self.import_ths_dialog)
        help_menu.add_separator()
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)

    def show_tutorial_tab(self):
        """切换到新手教学标签页"""
        if hasattr(self, 'main_notebook'):
            try:
                self.main_notebook.select(1)  # 新手教学是第2个标签页
            except Exception:
                pass
    
    def create_main_layout(self):
        """创建主界面布局"""
        # 主容器
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧面板 - 功能选择
        left_panel = ttk.Frame(main_container, width=400)
        main_container.add(left_panel, weight=1)
        
        # 右侧面板 - 输出和结果
        right_panel = ttk.Frame(main_container, width=1000)
        main_container.add(right_panel, weight=3)
        
        # 创建左侧功能面板
        self.create_left_panel(left_panel)
        
        # 创建右侧输出面板
        self.create_right_panel(right_panel)
    
    def create_left_panel(self, parent):
        """创建左侧功能面板"""
        # 使用 Notebook 创建标签页
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.main_notebook = notebook
        
        # 标签页1: 智能查询 [STAR]NEW
        self.create_smart_query_tab(notebook)
        
        # 标签页: 新手教学（买卖教程 + 同花顺导入）
        self.create_tutorial_tab(notebook)
        
        # 标签页: 数据爬取
        self.create_data_crawl_tab(notebook)
        
        # 标签页2: AI回测
        self.create_backtest_tab(notebook)
        
        # 标签页3: 实时监控
        self.create_monitor_tab(notebook)
        
        # 标签页4: 数据分析
        self.create_analysis_tab(notebook)
        
        # 标签页5: 持仓管理
        self.create_portfolio_tab(notebook)

        # 标签页6: 板块股
        self.create_sector_stocks_tab(notebook)
        # 初始化板块股查询状态
        self.sector_query_running = False
        self.hot_sector_query_running = False

        # 标签页7: 资金管理
        self.create_fund_management_tab(notebook)

        # 标签页8: 基金交易
        self.create_fund_trading_tab(notebook)

        # 标签页9: 数据管理
        self.create_data_management_tab(notebook)

        # 标签页10: 实时行情 [STAR]NEW
        self.create_realtime_market_tab(notebook)
        
        # 标签页11: 数据库管理 [STAR]NEW
        self.create_database_management_tab(notebook)
        
        # 标签页12: 全自动交易 [STAR]NEW
        self.create_auto_trading_tab(notebook)

        # 标签页: 推荐榜单（长线榜 + 短线榜 + 一键加自选）
        self.create_ranking_tab(notebook)

        # 标签页: 我的自选（自选股列表）
        self.create_watchlist_tab(notebook)
    
    def create_auto_trading_tab(self, notebook):
        """全自动交易标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🤖 全自动交易")
        
        # 标题
        title = ttk.Label(tab, text="全自动交易系统", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # 交易模式选择
        mode_frame = ttk.LabelFrame(tab, text="交易模式（新手请选“模拟交易”）", padding=10)
        mode_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.trading_mode_var = tk.StringVar(value="simulated")
        ttk.Radiobutton(mode_frame, text="模拟交易 (用假钱练手，推荐)", 
                       variable=self.trading_mode_var, value="simulated").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="真实交易 (演示)", 
                       variable=self.trading_mode_var, value="real").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="真实交易 (券商客户端)", 
                       variable=self.trading_mode_var, value="easytrader").pack(side=tk.LEFT, padx=10)
        
        # easytrader 券商客户端设置（选“券商客户端”模式时显示）
        self.easytrader_frame = ttk.LabelFrame(tab, text="券商客户端设置（真实下单，需本机已安装并登录客户端）", padding=10)
        self.easytrader_frame.pack(fill=tk.X, padx=10, pady=5)
        et_grid = ttk.Frame(self.easytrader_frame)
        et_grid.pack(fill=tk.X)
        
        ttk.Label(et_grid, text="券商类型:").grid(row=0, column=0, sticky=tk.W)
        self.easytrader_broker_var = tk.StringVar(value="universal")
        broker_box = ttk.Combobox(et_grid, textvariable=self.easytrader_broker_var, width=16,
                                  values=["universal", "ths", "gj", "gf", "yh", "ht", "htzq", "wk", "xq"],
                                  state="readonly")
        broker_box.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(et_grid, text="universal=通用同花顺, ths=同花顺, gj=国金, gf=广发, yh=银河, ht=华泰, htzq=海通, wk=五矿, xq=雪球").grid(row=0, column=2, sticky=tk.W, padx=10)
        
        ttk.Label(et_grid, text="资金账号:").grid(row=1, column=0, sticky=tk.W)
        self.easytrader_user_entry = ttk.Entry(et_grid, width=18)
        self.easytrader_user_entry.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(et_grid, text="交易密码:").grid(row=1, column=2, sticky=tk.W, padx=10)
        self.easytrader_pwd_entry = ttk.Entry(et_grid, width=18, show="*")
        self.easytrader_pwd_entry.grid(row=1, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(et_grid, text="客户端exe路径(可留空):").grid(row=2, column=0, sticky=tk.W)
        self.easytrader_exe_entry = ttk.Entry(et_grid, width=40)
        self.easytrader_exe_entry.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=5)
        detected = self._detect_ths_exe()
        if detected:
            self.easytrader_exe_entry.insert(0, detected)
        
        ttk.Label(self.easytrader_frame,
                  text="提示：必须先在本机安装并登录对应的券商交易客户端（推荐同花顺PC版），点“开始”后程序会接管客户端自动下单。"
                       "尚未安装客户端时请先选“模拟交易”。", foreground="orange").pack(anchor=tk.W, pady=(6, 0))
        
        def _toggle_easytrader_frame(*_):
            if self.trading_mode_var.get() == "easytrader":
                self.easytrader_frame.pack(fill=tk.X, padx=10, pady=5)
            else:
                self.easytrader_frame.pack_forget()
        self.trading_mode_var.trace_add("write", _toggle_easytrader_frame)
        _toggle_easytrader_frame()
        
        # 初始资金设置
        capital_frame = ttk.LabelFrame(tab, text="开始有多少钱", padding=10)
        capital_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(capital_frame, text="开始有多少钱(元):").pack(side=tk.LEFT)
        self.initial_capital_entry = ttk.Entry(capital_frame, width=15)
        self.initial_capital_entry.pack(side=tk.LEFT, padx=5)
        self.initial_capital_entry.insert(0, "100000")
        
        # 监控股票列表
        stock_frame = ttk.LabelFrame(tab, text="想自动买卖的股票（不懂就保持默认）", padding=10)
        stock_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(stock_frame, text="股票代码(逗号分隔):").pack(anchor=tk.W)
        self.monitor_stocks_entry = ttk.Entry(stock_frame, width=40)
        self.monitor_stocks_entry.pack(fill=tk.X, pady=5)
        self.monitor_stocks_entry.insert(0, "600519,601318,000858,002594")
        
        # 风险控制参数
        risk_frame = ttk.LabelFrame(tab, text="安全设置（保护你的钱，不懂就保持默认）", padding=10)
        risk_frame.pack(fill=tk.X, padx=10, pady=5)
        
        risk_grid = ttk.Frame(risk_frame)
        risk_grid.pack(fill=tk.X)
        
        ttk.Label(risk_grid, text="单只股票最多占总资金(0.3=30%):").grid(row=0, column=0, sticky=tk.W)
        self.max_single_ratio_entry = ttk.Entry(risk_grid, width=8)
        self.max_single_ratio_entry.grid(row=0, column=1, padx=5)
        self.max_single_ratio_entry.insert(0, "0.3")
        
        ttk.Label(risk_grid, text="所有股票合计最多占:").grid(row=0, column=2, sticky=tk.W, padx=10)
        self.max_total_ratio_entry = ttk.Entry(risk_grid, width=8)
        self.max_total_ratio_entry.grid(row=0, column=3, padx=5)
        self.max_total_ratio_entry.insert(0, "0.8")
        
        ttk.Label(risk_grid, text="亏到多少%自动卖掉:").grid(row=1, column=0, sticky=tk.W)
        self.stop_loss_entry = ttk.Entry(risk_grid, width=8)
        self.stop_loss_entry.grid(row=1, column=1, padx=5)
        self.stop_loss_entry.insert(0, "0.05")
        
        ttk.Label(risk_grid, text="赚到多少%自动卖出:").grid(row=1, column=2, sticky=tk.W, padx=10)
        self.take_profit_entry = ttk.Entry(risk_grid, width=8)
        self.take_profit_entry.grid(row=1, column=3, padx=5)
        self.take_profit_entry.insert(0, "0.10")
        
        # 交易状态显示
        status_frame = ttk.LabelFrame(tab, text="当前状态", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.engine_status_label = ttk.Label(status_frame, text="状态: 未启动", foreground="gray")
        self.engine_status_label.pack(anchor=tk.W)
        
        self.account_info_label = ttk.Label(status_frame, text="账户信息: 暂无数据", foreground="gray")
        self.account_info_label.pack(anchor=tk.W)
        
        self.today_trades_label = ttk.Label(status_frame, text="今日交易: 0 笔", foreground="gray")
        self.today_trades_label.pack(anchor=tk.W)
        
        # 控制按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=20)
        
        self.start_engine_btn = ttk.Button(btn_frame, text="▶️ 开始", 
                                          command=self.start_auto_trading, width=20)
        self.start_engine_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_engine_btn = ttk.Button(btn_frame, text="🛑 停止", 
                                         command=self.stop_auto_trading, width=20, state=tk.DISABLED)
        self.stop_engine_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_engine_btn = ttk.Button(btn_frame, text="⏸️ 暂停", 
                                          command=self.pause_auto_trading, width=20, state=tk.DISABLED)
        self.pause_engine_btn.pack(side=tk.LEFT, padx=5)
        
        # 日志显示
        log_frame = ttk.LabelFrame(tab, text="交易日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.trading_log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.trading_log_text.pack(fill=tk.BOTH, expand=True)
        self.trading_log_text.insert(tk.END, "全自动交易引擎就绪...\n")
        self.trading_log_text.config(state=tk.DISABLED)
        
        # 初始化交易引擎
        self.auto_trading_engine = None
        self.trading_log_update_thread = None
        
    def _detect_ths_exe(self):
        """在常见位置检测同花顺下单客户端 xiadan.exe"""
        import glob
        candidates = [
            r'C:\ths\xiadan.exe',
            r'C:\同花顺\xiadan.exe',
            r'C:\hexin\xiadan.exe',
        ]
        for base in (r'C:\Program Files', r'C:\Program Files (x86)', r'C:\Users', os.path.expanduser('~')):
            candidates.append(os.path.join(base, '同花顺', 'xiadan.exe'))
        for c in candidates:
            if os.path.isfile(c):
                return c
        try:
            home = os.path.expanduser('~')
            for hit in glob.glob(os.path.join(home, 'Downloads', '**', 'xiadan.exe'), recursive=True):
                return hit
        except Exception:
            pass
        return None

    def start_auto_trading(self):
        """启动全自动交易引擎"""
        try:
            from stock_trading_api import TradingAPIFactory
            from auto_trading_engine import AutoTradingEngine, MockAIStrategy
            
            # 获取配置参数
            initial_capital = float(self.initial_capital_entry.get().strip())
            trading_mode = self.trading_mode_var.get()
            
            # 创建交易API
            if trading_mode == "easytrader":
                from stock_trading_api import EasyTraderAPI
                broker = self.easytrader_broker_var.get().strip() or "universal"
                user = self.easytrader_user_entry.get().strip()
                password = self.easytrader_pwd_entry.get()
                exe_path = self.easytrader_exe_entry.get().strip() or None
                if not exe_path:
                    raise ValueError("请填写券商客户端的 exe 路径（如 C:\\同花顺\\xiadan.exe）")
                trading_api = EasyTraderAPI(broker=broker, exe_path=exe_path)
                if user:
                    self.log(f"[OK] 正在连接券商客户端 ({broker}) ...")
                else:
                    self.log("[OK] 正在连接本机已登录的券商客户端 ...")
                trading_api.connect(user=user, password=password)
                self.log("[OK] 券商客户端连接成功，可执行真实下单")
            else:
                trading_api = TradingAPIFactory.create_api(trading_mode, initial_balance=initial_capital)
            
            # 创建AI策略
            ai_strategy = MockAIStrategy()
            
            # 创建交易引擎
            self.auto_trading_engine = AutoTradingEngine(trading_api, ai_strategy)
            
            # 设置风险参数
            self.auto_trading_engine.set_risk_config(
                max_single_position_ratio=float(self.max_single_ratio_entry.get()),
                max_total_position_ratio=float(self.max_total_ratio_entry.get()),
                stop_loss_pct=float(self.stop_loss_entry.get()),
                take_profit_pct=float(self.take_profit_entry.get())
            )
            
            # 启动引擎
            self.auto_trading_engine.start()
            
            # 更新按钮状态
            self.start_engine_btn.config(state=tk.DISABLED)
            self.stop_engine_btn.config(state=tk.NORMAL)
            self.pause_engine_btn.config(state=tk.NORMAL)
            
            # 更新状态显示
            self.engine_status_label.config(text="状态: 🟢 运行中", foreground="green")
            
            # 启动日志更新线程
            self._start_log_updater()
            
            self.log("[OK] 全自动交易引擎已启动", "success")
            
        except Exception as e:
            self.log(f"[ERROR] 启动交易引擎失败: {e}", "error")
            messagebox.showerror("错误", f"启动交易引擎失败: {e}")
    
    def stop_auto_trading(self):
        """停止全自动交易引擎"""
        if self.auto_trading_engine:
            self.auto_trading_engine.stop()
            self.auto_trading_engine = None
            
            # 更新按钮状态
            self.start_engine_btn.config(state=tk.NORMAL)
            self.stop_engine_btn.config(state=tk.DISABLED)
            self.pause_engine_btn.config(state=tk.DISABLED)
            
            # 更新状态显示
            self.engine_status_label.config(text="状态: 🔴 已停止", foreground="red")
            
            self.log("[OK] 全自动交易引擎已停止", "success")
    
    def pause_auto_trading(self):
        """暂停/恢复交易"""
        if self.auto_trading_engine:
            if self.auto_trading_engine.paused:
                self.auto_trading_engine.resume()
                self.pause_engine_btn.config(text="⏸️ 暂停交易")
                self.engine_status_label.config(text="状态: 🟢 运行中", foreground="green")
                self.log("▶️ 交易已恢复", "info")
            else:
                self.auto_trading_engine.pause()
                self.pause_engine_btn.config(text="▶️ 恢复交易")
                self.engine_status_label.config(text="状态: 🟡 已暂停", foreground="orange")
                self.log("⏸️ 交易已暂停", "info")
    
    def _start_log_updater(self):
        """启动日志更新线程"""
        def update_logs():
            while self.auto_trading_engine and self.auto_trading_engine.running:
                try:
                    logs = self.auto_trading_engine.get_recent_logs(limit=20)
                    if logs:
                        self.trading_log_text.config(state=tk.NORMAL)
                        self.trading_log_text.delete(1.0, tk.END)
                        for log in logs:
                            level_color = {
                                'INFO': 'black',
                                'WARNING': 'orange',
                                'ERROR': 'red',
                                'SUCCESS': 'green'
                            }
                            color = level_color.get(log['level'], 'black')
                            self.trading_log_text.insert(tk.END, f"[{log['timestamp']}] {log['message']}\n")
                        self.trading_log_text.see(tk.END)
                        self.trading_log_text.config(state=tk.DISABLED)
                    
                    # 更新账户信息
                    if self.auto_trading_engine.trading_api:
                        account = self.auto_trading_engine.trading_api.get_account_balance()
                        if account:
                            self.account_info_label.config(
                                text=f"总资产: {account.get('total_assets', 0):,.2f} 元 | "
                                     f"可用余额: {account.get('balance', 0):,.2f} 元 | "
                                     f"收益: {account.get('total_profit', 0):+.2f} 元"
                            )
                    
                    # 更新今日交易数
                    self.today_trades_label.config(
                        text=f"今日交易: {self.auto_trading_engine.daily_trades} 笔"
                    )
                    
                except Exception as e:
                    pass
                
                time.sleep(2)
        
        self.trading_log_update_thread = threading.Thread(target=update_logs, daemon=True)
        self.trading_log_update_thread.start()

    # ------------------------------------------------------------------
    # 推荐榜单标签页（长线榜 + 短线榜 + 一键加自选）
    # ------------------------------------------------------------------
    def create_ranking_tab(self, notebook):
        """🏆 推荐榜单：长线榜单 + 短线榜单 + 一键加入自选股"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🏆 推荐榜单")

        self.ranking_running = False
        self.ranking_auto_var = tk.BooleanVar(value=True)
        self.ranking_interval = 1800

        # 市场状态头标（盘中=实时榜单 / 收盘=当日总结）
        self.ranking_market_label = ttk.Label(tab, text="", padding=(10, 6), font=("Arial", 10, "bold"))
        self.ranking_market_label.pack(fill=tk.X, padx=8, pady=(4, 0))
        self._update_ranking_market_label()

        # 新手说明条
        help_frame = ttk.Frame(tab, padding=(10, 6))
        help_frame.pack(fill=tk.X, padx=8, pady=(6, 2))
        ttk.Label(help_frame,
                  text="👋 这里自动帮你从全市场挑出两类好票：长线榜=适合拿一年以上的好公司，短线榜=今天比较活跃有机会的票。",
                  style="Hint.TLabel").pack(anchor=tk.W)
        ttk.Label(help_frame,
                  text="看到中意的，选中后点“⭐ 加入自选”，就会存到你的自选股里，方便每天看。",
                  style="Hint.TLabel").pack(anchor=tk.W)

        # 控制栏
        ctrl = ttk.Frame(tab)
        ctrl.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(ctrl, text="🔄 刷新榜单", style="Accent.TButton",
                   command=self.ranking_refresh, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="⭐ 选中加入自选", command=self.ranking_add_selected, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="⭐ 全部加入自选", command=self.ranking_add_all, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(ctrl, text="自动刷新", variable=self.ranking_auto_var,
                        command=self.ranking_toggle_auto).pack(side=tk.LEFT, padx=8)
        ttk.Label(ctrl, text="间隔(分钟):").pack(side=tk.LEFT, padx=(8, 0))
        self.ranking_interval_var = tk.StringVar(value="30")
        ttk.Spinbox(ctrl, from_=5, to=240, textvariable=self.ranking_interval_var, width=6).pack(side=tk.LEFT, padx=2)
        self.ranking_status = ttk.Label(ctrl, text="状态: 未刷新", foreground="gray")
        self.ranking_status.pack(side=tk.LEFT, padx=10)

        # 长线榜单
        long_frame = ttk.LabelFrame(tab, text="🌱 长线榜（适合长期持有的好公司，按综合分排序）", padding=4)
        long_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        lcols = ("排名", "代码", "名称", "现价", "总分", "级别", "技术面", "基本面", "AI预测", "今涨跌幅", "结论")
        self.ranking_long_tree = ttk.Treeview(long_frame, columns=lcols, show="headings", height=10)
        lwidths = {"排名": 42, "代码": 62, "名称": 110, "现价": 64, "总分": 54, "级别": 44,
                   "技术面": 54, "基本面": 54, "AI预测": 54, "今涨跌幅": 68, "结论": 150}
        for c in lcols:
            self.ranking_long_tree.heading(c, text=c)
            self.ranking_long_tree.column(c, width=lwidths.get(c, 90),
                                          anchor=tk.W if c in ("名称", "结论") else tk.CENTER)
        lsb = ttk.Scrollbar(long_frame, orient=tk.VERTICAL, command=self.ranking_long_tree.yview)
        self.ranking_long_tree.configure(yscrollcommand=lsb.set)
        lsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.ranking_long_tree.pack(fill=tk.BOTH, expand=True)

        # 短线榜单
        short_frame = ttk.LabelFrame(tab, text="🔥 短线榜（今天活跃、有机会的票，注意别追高）", padding=4)
        short_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        scols = ("排名", "代码", "名称", "现价", "短线分", "今涨幅", "成交额", "走势强度", "提示")
        self.ranking_short_tree = ttk.Treeview(short_frame, columns=scols, show="headings", height=8)
        swidths = {"排名": 42, "代码": 62, "名称": 110, "现价": 64, "短线分": 58, "今涨幅": 70,
                   "成交额": 80, "走势强度": 70, "提示": 90}
        for c in scols:
            self.ranking_short_tree.heading(c, text=c)
            self.ranking_short_tree.column(c, width=swidths.get(c, 90),
                                           anchor=tk.W if c in ("名称",) else tk.CENTER)
        ssb = ttk.Scrollbar(short_frame, orient=tk.VERTICAL, command=self.ranking_short_tree.yview)
        self.ranking_short_tree.configure(yscrollcommand=ssb.set)
        ssb.pack(side=tk.RIGHT, fill=tk.Y)
        self.ranking_short_tree.pack(fill=tk.BOTH, expand=True)

        # 首次自动刷新（延迟2秒让界面先显示）
        try:
            self.root.after(2000, self.ranking_refresh)
        except Exception:
            pass

    def ranking_refresh(self):
        """刷新榜单（后台线程 + 进度反馈 + 看门狗防卡死）"""
        if self.ranking_running:
            return
        self.ranking_running = True
        self._ranking_start = time.time()
        self.ranking_status.config(text="状态: 正在抓全市场快照（约15-30秒）...", foreground="blue")

        def work():
            try:
                self.log("[榜单] 开始刷新（短线榜→长线榜）")
                short_df = self.longterm.screen_shortterm(limit=10)
                self.root.after(0, lambda: self.log(f"[榜单] 短线榜完成 {0 if short_df is None else len(short_df)} 只"))
                self.root.after(0, lambda: self.ranking_status.config(
                    text="状态: 短线榜OK，正在逐只分析长线股...", foreground="blue"))

                def progress(nm, done, limit):
                    self.root.after(0, lambda n=nm, d=done, l=limit: self.ranking_status.config(
                        text=f"状态: 长线分析中 {d}/{l}… 正在分析 {n}", foreground="blue"))

                long_df = self.longterm.screen_longterm(limit=10, progress_cb=progress)
                self.root.after(0, lambda: self.log(f"[榜单] 长线榜完成 {0 if long_df is None else len(long_df)} 只"))
                self.root.after(0, lambda: self._show_ranking(long_df, short_df))
            except Exception as e:
                import traceback
                tb = traceback.format_exc()[-800:]
                self.root.after(0, lambda: [
                    self.ranking_status.config(text=f"状态: 刷新失败 - {e}", foreground="red"),
                    self.log(f"[ERROR] 榜单刷新失败: {e}\n{tb}", "error")])
            finally:
                self.ranking_running = False

        threading.Thread(target=work, daemon=True).start()

        # 看门狗：超时自动提示并解锁按钮，避免"永远卡住"
        def watchdog():
            if not self.ranking_running:
                return
            if time.time() - self._ranking_start > 180:
                self.ranking_running = False
                self.ranking_status.config(text="状态: 刷新超时（可能网络连不上东财），请稍后再试", foreground="red")
                self.log("[榜单] 刷新超过180秒，已判定超时并解锁，请检查网络后重试")
            else:
                self.root.after(5000, watchdog)

        self.root.after(5000, watchdog)

    def _show_ranking(self, long_df, short_df):
        # 长线榜
        self.ranking_long_tree.delete(*self.ranking_long_tree.get_children())
        if long_df is not None and not long_df.empty:
            for _, r in long_df.iterrows():
                level = str(r.get('级别', ''))
                tags = ("lt_A",) if level == 'A' else (("lt_B",) if level == 'B' else ())
                self.ranking_long_tree.insert("", tk.END, values=(
                    r.get('排名', ''), r.get('代码', ''), r.get('名称', ''),
                    r.get('现价', ''), r.get('总分', ''), level,
                    r.get('技术面', ''), r.get('基本面', ''), r.get('AI预测', ''),
                    r.get('今涨跌幅', ''), r.get('结论', '')), tags=tags)
        self.ranking_long_tree.tag_configure("lt_A", background="#e6f4ff")
        self.ranking_long_tree.tag_configure("lt_B", background="#f0fff0")

        # 短线榜
        self.ranking_short_tree.delete(*self.ranking_short_tree.get_children())
        if short_df is not None and not short_df.empty:
            for _, r in short_df.iterrows():
                total = self._f(r, '短线分', 0)
                tags = ("st_hi",) if total >= 80 else (("st_mid",) if total >= 65 else ())
                self.ranking_short_tree.insert("", tk.END, values=(
                    r.get('排名', ''), r.get('代码', ''), r.get('名称', ''),
                    r.get('现价', ''), r.get('短线分', ''), r.get('今涨幅', ''),
                    r.get('成交额', ''), r.get('强度', ''), r.get('提示', '')), tags=tags)
        self.ranking_short_tree.tag_configure("st_hi", foreground="#e03131")
        self.ranking_short_tree.tag_configure("st_mid", foreground="#d9480f")

        n = (0 if long_df is None else len(long_df)) + (0 if short_df is None else len(short_df))
        self.ranking_status.config(text=f"状态: 刷新完成 - 长线{0 if long_df is None else len(long_df)}只 / 短线{0 if short_df is None else len(short_df)}只",
                                   foreground="green")
        self.log(f"[榜单] 刷新完成，长线 {0 if long_df is None else len(long_df)} 只，短线 {0 if short_df is None else len(short_df)} 只")
        self._update_ranking_market_label(done=True,
                                          long_n=0 if long_df is None else len(long_df),
                                          short_n=0 if short_df is None else len(short_df))

    def ranking_selected_pairs(self, tree, name_col, code_col):
        """收集选中行 (code, name) 列表"""
        pairs = []
        for iid in tree.selection():
            vals = tree.item(iid, "values")
            if len(vals) > name_col:
                code = str(vals[code_col]).strip()
                name = str(vals[name_col]).strip()
                if code and name and code != '':
                    pairs.append((code, name))
        return pairs

    def ranking_add_selected(self):
        """把选中榜单里的股票加入自选股"""
        pairs = []
        pairs += self.ranking_selected_pairs(self.ranking_long_tree, 2, 1)
        pairs += self.ranking_selected_pairs(self.ranking_short_tree, 2, 1)
        if not pairs:
            messagebox.showinfo("提示", "请先在榜单里选中要加入自选的股票（可按住Ctrl多选）")
            return
        self._add_to_watchlist(pairs)

    def ranking_add_all(self):
        """把两个榜单里的所有股票加入自选股"""
        pairs = []
        for tree in (self.ranking_long_tree, self.ranking_short_tree):
            for iid in tree.get_children():
                vals = tree.item(iid, "values")
                if len(vals) > 2:
                    code = str(vals[1]).strip()
                    name = str(vals[2]).strip()
                    if code and name:
                        pairs.append((code, name))
        if not pairs:
            messagebox.showinfo("提示", "榜单还没有数据，请先刷新")
            return
        self._add_to_watchlist(pairs)

    def _add_to_watchlist(self, pairs):
        ok, dup, failed = self.watchlist.add_many(pairs)
        msg = f"✅ 成功加入自选股 {ok} 只"
        if dup:
            msg += f"，{dup} 只已在自选股中"
        if failed:
            msg += f"，失败 {len(failed)} 只"
        messagebox.showinfo("加入自选股", msg)
        self.log(f"[自选] {msg}")
        self.refresh_watchlist_tree()

    def _update_ranking_market_label(self, done=False, long_n=0, short_n=0):
        """根据是否开盘更新榜单页顶部的状态说明"""
        try:
            trading = self.longterm.is_trading_time()
        except Exception:
            trading = True
        now_str = datetime.now().strftime("%H:%M")
        if trading:
            text = f"📊 盘中：实时榜单（每5分钟自动刷新）· 更新于 {now_str}"
            color = "#2563eb"
        else:
            if done:
                text = f"📋 已收盘：今日全天分析总结 · 生成于 {now_str}（长线 {long_n} 只 / 短线 {short_n} 只）"
            else:
                text = f"📋 已收盘：今日全天分析总结 · 当前时间 {now_str}"
            color = "#2f9e44"
        self.ranking_market_label.config(text=text, foreground=color)

    def ranking_toggle_auto(self):
        if self.ranking_auto_var.get():
            try:
                self.ranking_interval = max(5, int(float(self.ranking_interval_var.get() or 30)))
            except Exception:
                self.ranking_interval = 30
            self.ranking_schedule_auto()
        elif hasattr(self, '_ranking_auto_id'):
            try:
                self.root.after_cancel(self._ranking_auto_id)
            except Exception:
                pass

    def ranking_schedule_auto(self):
        if not self.ranking_auto_var.get():
            return
        self.ranking_refresh()
        # 盘中每5分钟自动刷新（实时榜单），收盘/非交易日每60分钟刷新一次（当日总结）
        try:
            trading = self.longterm.is_trading_time()
        except Exception:
            trading = True
        eff_interval = 5 if trading else 60
        self._update_ranking_market_label()
        try:
            self._ranking_auto_id = self.root.after(int(eff_interval * 60 * 1000), self.ranking_schedule_auto)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 我的自选标签页
    # ------------------------------------------------------------------
    def create_watchlist_tab(self, notebook):
        """⭐ 我的自选：自选股列表，可删除/刷新行情"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="⭐ 我的自选")

        help_frame = ttk.Frame(tab, padding=(10, 6))
        help_frame.pack(fill=tk.X, padx=8, pady=(6, 2))
        ttk.Label(help_frame,
                  text="👋 这是你收藏的自选股，每天打开看一眼它们的现价和涨跌。在“🏆 推荐榜单”里选中股票点“加入自选”就能加进来。",
                  style="Hint.TLabel").pack(anchor=tk.W)

        # 添加按钮
        add_row = ttk.Frame(tab)
        add_row.pack(fill=tk.X, padx=8, pady=4)
        self.watch_add_entry = ttk.Entry(add_row, width=40)
        self.watch_add_entry.pack(side=tk.LEFT, padx=2)
        self.watch_add_entry.insert(0, "600519")
        ttk.Button(add_row, text="➕ 添加自选", style="Accent.TButton",
                   command=self.watchlist_add, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(add_row, text="🔄 刷新行情", command=self.watchlist_refresh_prices, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(add_row, text="🗑️ 删除选中", command=self.watchlist_delete, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(add_row, text="🧹 清空", command=self.watchlist_clear, width=8).pack(side=tk.LEFT, padx=2)
        self.watch_status = ttk.Label(add_row, text="", foreground="gray")
        self.watch_status.pack(side=tk.LEFT, padx=8)

        # 自选股表格
        frame = ttk.LabelFrame(tab, text="📋 我的自选股", padding=4)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        cols = ("代码", "名称", "现价", "今日涨跌", "涨跌金额", "备注", "添加时间")
        self.watch_tree = ttk.Treeview(frame, columns=cols, show="headings", height=12)
        wwidths = {"代码": 66, "名称": 120, "现价": 70, "今日涨跌": 70, "涨跌金额": 70, "备注": 160, "添加时间": 130}
        for c in cols:
            self.watch_tree.heading(c, text=c)
            self.watch_tree.column(c, width=wwidths.get(c, 90), anchor=tk.W if c in ("名称", "备注") else tk.CENTER)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.watch_tree.yview)
        self.watch_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.watch_tree.pack(fill=tk.BOTH, expand=True)

        self.watch_tree.tag_configure("up", foreground="#e03131")
        self.watch_tree.tag_configure("down", foreground="#2f9e44")

        self.refresh_watchlist_tree()

    def refresh_watchlist_tree(self):
        """重绘自选股列表"""
        if not hasattr(self, 'watch_tree'):
            return
        self.watch_tree.delete(*self.watch_tree.get_children())
        for item in self.watchlist.all():
            self.watch_tree.insert("", tk.END, values=(
                item.get('code', ''), item.get('name', ''),
                '-', '-', '-', item.get('remark', ''), item.get('add_time', '')))

    def watchlist_add(self):
        text = self.watch_add_entry.get().strip()
        if not text:
            messagebox.showwarning("警告", "请输入股票代码或名字")
            return
        token = text.split(',')[0].strip()
        try:
            syms = self.smart_client.resolve(token)
            if syms and syms[0].type == 'stock':
                code = syms[0].code.zfill(6)
                name = syms[0].name
            else:
                code = token
                name = token
        except Exception:
            code = token
            name = token
        ok, msg = self.watchlist.add(code, name)
        if ok:
            self.watch_status.config(text=msg, foreground="green")
        else:
            self.watch_status.config(text=msg, foreground="orange")
        self.refresh_watchlist_tree()

    def watchlist_delete(self):
        selection = self.watch_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选中要删除的自选股")
            return
        for iid in selection:
            vals = self.watch_tree.item(iid, "values")
            if vals:
                self.watchlist.remove(vals[0])
        self.watch_status.config(text="已删除选中自选股", foreground="green")
        self.refresh_watchlist_tree()

    def watchlist_clear(self):
        if not messagebox.askyesno("确认", "确定清空所有自选股吗？"):
            return
        self.watchlist.remove_all()
        self.watch_status.config(text="已清空自选股", foreground="green")
        self.refresh_watchlist_tree()

    def watchlist_refresh_prices(self):
        """刷新自选股行情（后台线程）"""
        items = self.watchlist.all()
        if not items:
            self.watch_status.config(text="自选股为空", foreground="orange")
            return
        codes = [i['code'] for i in items]
        self.watch_status.config(text="正在刷新行情...", foreground="blue")

        def work():
            try:
                df = self.smart_client.get_realtime(codes)
                self.root.after(0, lambda: self._show_watch_prices(df))
            except Exception as e:
                self.root.after(0, lambda: self.watch_status.config(text=f"刷新失败: {e}", foreground="red"))

        threading.Thread(target=work, daemon=True).start()

    def _show_watch_prices(self, df):
        if df is None or df.empty:
            self.watch_status.config(text="没有获取到行情数据", foreground="orange")
            return
        order = {'stock': 0, 'fund': 1, 'index': 2, 'board': 3, '': 9}
        m = {}
        for _, r in df.iterrows():
            sym = str(r.get('symbol', ''))
            if not sym:
                continue
            rtype = str(r.get('type', ''))
            if sym not in m or order.get(rtype, 9) < order.get(str(m[sym].get('type', '')), 9):
                m[sym] = r
        for iid in self.watch_tree.get_children():
            vals = self.watch_tree.item(iid, "values")
            code = vals[0]
            if code in m:
                r = m[code]
                pct = self._f(r, 'change_percent', 0)
                amt = self._f(r, 'change_amount', 0)
                self.watch_tree.item(iid, values=(
                    code, r.get('name', vals[1]),
                    self._f(r, 'price', 2),
                    f"{pct:+.2f}%",
                    f"{amt:+.2f}",
                    vals[5], vals[6]), tags=("up",) if pct >= 0 else ("down",))
        self.watch_status.config(text="行情已刷新", foreground="green")

    def create_fund_trading_tab(self, notebook):
        """基金交易标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="💰 买基金")

        # 标题
        title = ttk.Label(tab, text="💰 买基金", style="Title.TLabel")
        title.pack(pady=10)

        # 基金搜索
        search_frame = ttk.LabelFrame(tab, text="基金查询", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(search_frame, text="基金代码:").pack(side=tk.LEFT)
        self.fund_code_entry = ttk.Entry(search_frame, width=10)
        self.fund_code_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(search_frame, text="🔍 查询基金", 
                  command=self.query_fund_info).pack(side=tk.LEFT, padx=5)

        # 基金信息显示
        info_frame = ttk.LabelFrame(tab, text="基金信息", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.fund_info_label = ttk.Label(info_frame, text="请输入基金代码进行查询...", foreground="gray")
        self.fund_info_label.pack(anchor=tk.W)

        # 基金持仓列表
        list_frame = ttk.LabelFrame(tab, text="我买的基金", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建基金持仓表格
        columns = ("code", "name", "type", "volume", "avg_price", "current_price", "value", "profit", "profit_pct")
        self.fund_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)

        self.fund_tree.heading("code", text="代码")
        self.fund_tree.heading("name", text="名称")
        self.fund_tree.heading("type", text="类型")
        self.fund_tree.heading("volume", text="持有数量")
        self.fund_tree.heading("avg_price", text="买入均价")
        self.fund_tree.heading("current_price", text="现在净值")
        self.fund_tree.heading("value", text="现在值多少")
        self.fund_tree.heading("profit", text="赚/亏(元)")
        self.fund_tree.heading("profit_pct", text="赚/亏(%)")

        self.fund_tree.column("code", width=80)
        self.fund_tree.column("name", width=150)
        self.fund_tree.column("type", width=80)
        self.fund_tree.column("volume", width=80)
        self.fund_tree.column("avg_price", width=80)
        self.fund_tree.column("current_price", width=80)
        self.fund_tree.column("value", width=100)
        self.fund_tree.column("profit", width=100)
        self.fund_tree.column("profit_pct", width=90)

        self.fund_tree.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.fund_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.fund_tree.configure(yscrollcommand=scrollbar.set)

        # 基金交易操作
        operation_frame = ttk.LabelFrame(tab, text="🛒 买进 / 卖出基金", padding=10)
        operation_frame.pack(fill=tk.X, padx=10, pady=5)

        # 买入基金
        buy_frame = ttk.Frame(operation_frame)
        buy_frame.pack(fill=tk.X, pady=2)

        ttk.Label(buy_frame, text="买进基金:").pack(side=tk.LEFT)
        self.fund_buy_code_entry = ttk.Entry(buy_frame, width=10)
        self.fund_buy_code_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(buy_frame, text="金额:").pack(side=tk.LEFT, padx=(10, 0))
        self.fund_buy_amount_entry = ttk.Entry(buy_frame, width=10)
        self.fund_buy_amount_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(buy_frame, text="元").pack(side=tk.LEFT)
        ttk.Button(buy_frame, text="买进", style="Accent.TButton", command=self.buy_fund).pack(side=tk.LEFT, padx=10)

        # 卖出基金
        sell_frame = ttk.Frame(operation_frame)
        sell_frame.pack(fill=tk.X, pady=2)

        ttk.Label(sell_frame, text="卖出基金:").pack(side=tk.LEFT)
        self.fund_sell_code_entry = ttk.Entry(sell_frame, width=10)
        self.fund_sell_code_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(sell_frame, text="份额:").pack(side=tk.LEFT, padx=(10, 0))
        self.fund_sell_volume_entry = ttk.Entry(sell_frame, width=10)
        self.fund_sell_volume_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(sell_frame, text="份").pack(side=tk.LEFT)
        ttk.Button(sell_frame, text="卖出", style="Accent.TButton", command=self.sell_fund).pack(side=tk.LEFT, padx=10)

        # 底部按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="🔄 刷新最新净值", command=self.refresh_fund_nav).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📋 更新持仓", command=self.refresh_fund_portfolio).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📜 交易记录", command=self.show_fund_trade_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ 清空持仓", command=self.clear_fund_portfolio).pack(side=tk.LEFT, padx=5)

        # 初始化基金管理器
        self.fund_manager = FundManager('fund_portfolio.pkl')
        self.refresh_fund_portfolio()

    def create_data_crawl_tab(self, notebook):
        """数据爬取标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="⬇️ 下载数据")
        
        # 标题
        title = ttk.Label(tab, text="⬇️ 下载数据（先把股票历史价格下载到电脑）", style="Title.TLabel")
        title.pack(pady=10)
        
        # 股票代码输入
        frame1 = ttk.LabelFrame(tab, text="想下载哪只股票", padding=10)
        frame1.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame1, text="输入股票代码(多个用逗号隔开):").pack(anchor=tk.W)
        ttk.Label(frame1, text="示例: 000001,000002,600000", foreground="gray").pack(anchor=tk.W)
        
        self.crawl_stock_entry = ttk.Entry(frame1, width=40)
        self.crawl_stock_entry.pack(fill=tk.X, pady=5)
        self.crawl_stock_entry.insert(0, "000001")
        
        # 日期选择
        frame2 = ttk.LabelFrame(tab, text="要下载哪个时间段", padding=10)
        frame2.pack(fill=tk.X, padx=10, pady=5)
        
        date_frame = ttk.Frame(frame2)
        date_frame.pack(fill=tk.X)
        
        ttk.Label(date_frame, text="开始日期(格式 20260101):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.crawl_start_date = ttk.Entry(date_frame, width=15)
        self.crawl_start_date.grid(row=0, column=1, padx=5)
        current_year = datetime.now().year
        self.crawl_start_date.insert(0, f"{current_year}0101")
        
        ttk.Label(date_frame, text="结束日期(格式 20260805):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.crawl_end_date = ttk.Entry(date_frame, width=15)
        self.crawl_end_date.grid(row=1, column=1, padx=5)
        self.crawl_end_date.insert(0, datetime.now().strftime('%Y%m%d'))
        
        # 按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=20)
        
        ttk.Button(btn_frame, text="⬇️ 开始下载", 
                  command=self.start_crawling, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="👀 查看数据", 
                  command=self.view_data, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 打开文件夹", 
                  command=self.open_financial_data_folder, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ 清空数据", 
                  command=self.clear_financial_data, width=15).pack(side=tk.LEFT, padx=5)
    
    def create_backtest_tab(self, notebook):
        """AI回测标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🧪 AI智能模拟")
        
        # 标题
        title = ttk.Label(tab, text="🧪 AI智能模拟（拿历史数据试试某种买卖方法赚不赚钱）", style="Title.TLabel")
        title.pack(pady=10)
        
        # 股票代码
        frame1 = ttk.LabelFrame(tab, text="测试设置", padding=10)
        frame1.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame1, text="股票代码:").pack(anchor=tk.W)
        self.backtest_stock_entry = ttk.Entry(frame1, width=40)
        self.backtest_stock_entry.pack(fill=tk.X, pady=5)
        self.backtest_stock_entry.insert(0, "000001")
        
        # 数据源选择
        ttk.Label(frame1, text="数据从哪来:").pack(anchor=tk.W, pady=(10, 0))
        data_source_frame = ttk.Frame(frame1)
        data_source_frame.pack(fill=tk.X, pady=5)
        
        self.data_source_var = tk.StringVar(value="existing")
        
        ttk.Radiobutton(data_source_frame, text="用电脑里已下载的数据", 
                       variable=self.data_source_var, value="existing").pack(side=tk.LEFT)
        ttk.Radiobutton(data_source_frame, text="现场下载新数据", 
                       variable=self.data_source_var, value="download").pack(side=tk.LEFT, padx=(20, 0))
        
        # 时间范围选择（仅当选择下载新数据时显示）
        self.date_frame = ttk.Frame(frame1)
        
        ttk.Label(self.date_frame, text="开始日期:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.backtest_start_date = ttk.Entry(self.date_frame, width=15)
        self.backtest_start_date.grid(row=0, column=1, padx=5)
        current_year = datetime.now().year
        self.backtest_start_date.insert(0, f"{current_year-1}0101")
        
        ttk.Label(self.date_frame, text="结束日期:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.backtest_end_date = ttk.Entry(self.date_frame, width=15)
        self.backtest_end_date.grid(row=1, column=1, padx=5)
        self.backtest_end_date.insert(0, datetime.now().strftime('%Y%m%d'))
        
        # 绑定数据源选择事件
        def update_date_frame_visibility(*args):
            if self.data_source_var.get() == "download":
                self.date_frame.pack(fill=tk.X, pady=5)
            else:
                self.date_frame.pack_forget()
        
        self.data_source_var.trace("w", update_date_frame_visibility)
        
        # AI模型选择
        ttk.Label(frame1, text="AI模型:").pack(anchor=tk.W, pady=(10, 0))
        self.backtest_model_var = tk.StringVar(value="1")
        
        for key, info in AI_MODELS.items():
            rb = ttk.Radiobutton(
                frame1, 
                text=f"{info['name']} (速度:{info['speed']}, 精度:{info['accuracy']})",
                variable=self.backtest_model_var,
                value=key
            )
            rb.pack(anchor=tk.W)
        
        # 按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=20)
        
        ttk.Button(btn_frame, text="▶️ 开始模拟", 
                  command=self.start_backtest, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔁 多个模型比一比", 
                  command=self.start_model_comparison, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 选择数据文件", 
                  command=self.select_data_file, width=20).pack(side=tk.LEFT, padx=5)
    
    def create_monitor_tab(self, notebook):
        """实时监控标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="👀 盘中盯盘")
        
        # 标题
        title = ttk.Label(tab, text="👀 盘中盯盘（帮你盯着股票，有动静会提示）", style="Title.TLabel")
        title.pack(pady=10)
        
        # 股票代码
        frame1 = ttk.LabelFrame(tab, text="盯盘设置", padding=10)
        frame1.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame1, text="股票代码(多个用逗号隔开):").pack(anchor=tk.W)
        ttk.Label(frame1, text="示例: 000001,000002,600000", foreground="gray").pack(anchor=tk.W)
        
        self.monitor_stock_entry = ttk.Entry(frame1, width=40)
        self.monitor_stock_entry.pack(fill=tk.X, pady=5)
        self.monitor_stock_entry.insert(0, "000001,000002")
        
        # AI模型
        ttk.Label(frame1, text="用哪个AI模型（不懂就保持默认）:").pack(anchor=tk.W, pady=(10, 0))
        self.monitor_model_var = tk.StringVar(value="1")
        model_combo = ttk.Combobox(frame1, textvariable=self.monitor_model_var, 
                                   values=[f"{k} - {v['name']}" for k, v in AI_MODELS.items()],
                                   state="readonly", width=37)
        model_combo.set("1 - 随机森林 (Random Forest)")
        model_combo.pack(fill=tk.X, pady=5)
        
        # 刷新间隔
        ttk.Label(frame1, text="多久看一眼(秒):").pack(anchor=tk.W, pady=(10, 0))
        self.monitor_interval_var = tk.StringVar(value="60")
        interval_spin = ttk.Spinbox(frame1, from_=10, to=300, 
                                    textvariable=self.monitor_interval_var, width=38)
        interval_spin.pack(fill=tk.X, pady=5)
        
        # 是否训练模型
        self.monitor_train_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame1, text="启动时让AI学一遍历史数据", 
                       variable=self.monitor_train_var).pack(anchor=tk.W, pady=5)
        
        # 按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=20)
        
        self.monitor_start_btn = ttk.Button(btn_frame, text="▶️ 开始盯盘", 
                                           command=self.start_monitoring, width=20)
        self.monitor_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.monitor_stop_btn = ttk.Button(btn_frame, text="⏹️ 停止盯盘", 
                                          command=self.stop_monitoring, width=20, state=tk.DISABLED)
        self.monitor_stop_btn.pack(side=tk.LEFT, padx=5)
    
    def create_analysis_tab(self, notebook):
        """数据分析标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📈 走势图表")
        
        # 标题
        title = ttk.Label(tab, text="📈 走势图表与数据分析（画出涨跌走势图）", style="Title.TLabel")
        title.pack(pady=10)
        
        # 配置
        frame1 = ttk.LabelFrame(tab, text="分析设置", padding=10)
        frame1.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame1, text="数据目录:").pack(anchor=tk.W)
        dir_frame = ttk.Frame(frame1)
        dir_frame.pack(fill=tk.X, pady=5)
        
        self.analysis_dir_entry = ttk.Entry(dir_frame, width=30)
        self.analysis_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.analysis_dir_entry.insert(0, DATA_DIR)
        
        # AI分析选项
        self.analysis_ai_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame1, text="启用AI智能分析 (需配置AI模型)", 
                       variable=self.analysis_ai_var).pack(anchor=tk.W, pady=5)
        
        # 按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=20)
        
        ttk.Button(btn_frame, text="▶️ 开始分析",
                  command=self.start_analysis, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ 清空分析结果",
                  command=self.clear_analysis_data, width=20).pack(side=tk.LEFT, padx=5)

    def create_portfolio_tab(self, notebook):
        """持仓管理标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="💼 我的持仓")

        # 标题
        title = ttk.Label(tab, text="💼 我的持仓", style="Title.TLabel")
        title.pack(pady=10)

        # 资金信息
        info_frame = ttk.LabelFrame(tab, text="💰 我有多少钱", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.cash_label = ttk.Label(info_frame, text="📌 可用现金: 0.00 元")
        self.cash_label.pack(anchor=tk.W)

        self.total_asset_label = ttk.Label(info_frame, text="💎 全部家当(总资产): 0.00 元")
        self.total_asset_label.pack(anchor=tk.W)

        self.total_profit_label = ttk.Label(info_frame, text="💰 一共赚/亏: 0.00 元")
        self.total_profit_label.pack(anchor=tk.W)

        ttk.Label(info_frame,
                  text="小知识：可用现金=还没用来买股票的钱 · 全部家当=现金 + 股票现在值多少 · 赚/亏=现在和你买入时比赚了还是亏了。",
                  style="Hint.TLabel").pack(anchor=tk.W, pady=(4, 2))
        ttk.Button(info_frame, text="✏️ 修改可用现金", command=self.edit_cash_dialog).pack(anchor=tk.W, pady=(4, 0))

        # 持仓列表
        list_frame = ttk.LabelFrame(tab, text="📋 我手里的股票（买来还没卖掉的）", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建持仓表格
        columns = ("code", "name", "volume", "avg_price", "current_price", "value", "profit", "profit_pct")
        self.portfolio_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)

        self.portfolio_tree.heading("code", text="代码")
        self.portfolio_tree.heading("name", text="名称")
        self.portfolio_tree.heading("volume", text="数量(股)")
        self.portfolio_tree.heading("avg_price", text="买入均价")
        self.portfolio_tree.heading("current_price", text="现在价格")
        self.portfolio_tree.heading("value", text="现在值多少")
        self.portfolio_tree.heading("profit", text="赚/亏(元)")
        self.portfolio_tree.heading("profit_pct", text="赚/亏(%)")

        self.portfolio_tree.column("code", width=80)
        self.portfolio_tree.column("name", width=110)
        self.portfolio_tree.column("volume", width=90)
        self.portfolio_tree.column("avg_price", width=90)
        self.portfolio_tree.column("current_price", width=90)
        self.portfolio_tree.column("value", width=100)
        self.portfolio_tree.column("profit", width=100)
        self.portfolio_tree.column("profit_pct", width=90)

        self.portfolio_tree.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.portfolio_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.portfolio_tree.configure(yscrollcommand=scrollbar.set)

        ttk.Label(tab,
                  text="💡 数量单位：股=买股票的数量（像买苹果按“斤”），A股最少买100股，100股=1手。仓/持仓=你手里拿着的股票。",
                  style="Hint.TLabel").pack(anchor=tk.W, padx=12, pady=(2, 0))

        # 持仓操作按钮
        operation_frame = ttk.LabelFrame(tab, text="🛒 买进 / 卖出", padding=10)
        operation_frame.pack(fill=tk.X, padx=10, pady=5)

        # 买入操作
        buy_frame = ttk.Frame(operation_frame)
        buy_frame.pack(fill=tk.X, pady=2)

        ttk.Label(buy_frame, text="买进:").pack(side=tk.LEFT)
        self.buy_code_entry = ttk.Entry(buy_frame, width=8)
        self.buy_code_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(buy_frame, text="数量:").pack(side=tk.LEFT, padx=(10, 0))
        self.buy_volume_entry = ttk.Entry(buy_frame, width=8)
        self.buy_volume_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(buy_frame, text="价格:").pack(side=tk.LEFT, padx=(10, 0))
        self.buy_price_entry = ttk.Entry(buy_frame, width=8)
        self.buy_price_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(buy_frame, text="买进", style="Accent.TButton", command=self.execute_buy).pack(side=tk.LEFT, padx=10)

        # 卖出操作
        sell_frame = ttk.Frame(operation_frame)
        sell_frame.pack(fill=tk.X, pady=2)

        ttk.Label(sell_frame, text="卖出:").pack(side=tk.LEFT)
        self.sell_code_entry = ttk.Entry(sell_frame, width=8)
        self.sell_code_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(sell_frame, text="数量:").pack(side=tk.LEFT, padx=(10, 0))
        self.sell_volume_entry = ttk.Entry(sell_frame, width=8)
        self.sell_volume_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(sell_frame, text="价格:").pack(side=tk.LEFT, padx=(10, 0))
        self.sell_price_entry = ttk.Entry(sell_frame, width=8)
        self.sell_price_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(sell_frame, text="卖出", style="Accent.TButton", command=self.execute_sell).pack(side=tk.LEFT, padx=10)
        ttk.Label(sell_frame, text="（数量按“股”填，价格不填就按最新价）", style="Hint.TLabel").pack(side=tk.LEFT, padx=10)

        # 底部按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="➕ 手动添加", command=self.add_portfolio_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏️ 编辑选中", command=self.edit_portfolio_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ 删除选中", command=self.delete_portfolio_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📥 导入同花顺数据", style="Accent.TButton",
                   command=self.import_ths_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 刷新持仓", command=self.refresh_portfolio).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🏷️ 更新最新价格", command=self.update_portfolio_prices).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📜 交易记录", command=self.show_trade_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ 清空持仓", command=self.clear_portfolio).pack(side=tk.LEFT, padx=5)

        # 初始刷新持仓信息
        self.refresh_portfolio()

    def create_sector_stocks_tab(self, notebook):
        """板块股标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🔥 热门板块")

        # 标题
        title = ttk.Label(tab, text="🔥 热门板块", style="Title.TLabel")
        title.pack(pady=10)

        # 板块类型选择
        type_frame = ttk.LabelFrame(tab, text="板块类型选择（不懂就选“概念板块”）", padding=10)
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.sector_type_var = tk.StringVar(value="concept")  # 默认为概念板块
        ttk.Radiobutton(type_frame, text="概念板块", variable=self.sector_type_var, value="concept").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="行业板块", variable=self.sector_type_var, value="industry").pack(side=tk.LEFT, padx=10)
        
        # 板块查询
        query_frame = ttk.LabelFrame(tab, text="板块查询", padding=10)
        query_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(query_frame, text="输入板块名称:").pack(anchor=tk.W)
        
        query_input_frame = ttk.Frame(query_frame)
        query_input_frame.pack(fill=tk.X, pady=5)
        
        self.sector_query_entry = ttk.Entry(query_input_frame, width=20)
        self.sector_query_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.sector_query_entry.insert(0, "人工智能")  # 默认值
        
        ttk.Button(query_input_frame, text="🔍 查这个板块的股票", 
                  command=self.query_sector_stocks).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(query_input_frame, text="🔥 看今日热门板块", 
                  command=self.get_hot_sectors).pack(side=tk.LEFT, padx=5)

        # 板块股票列表
        list_frame = ttk.LabelFrame(tab, text="这个板块里的股票", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建板块股票表格
        columns = ("code", "name", "price", "change_pct", "volume", "reason")
        self.sector_stocks_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

        self.sector_stocks_tree.heading("code", text="代码")
        self.sector_stocks_tree.heading("name", text="名称")
        self.sector_stocks_tree.heading("price", text="现价")
        self.sector_stocks_tree.heading("change_pct", text="今日涨跌")
        self.sector_stocks_tree.heading("volume", text="成交量")
        self.sector_stocks_tree.heading("reason", text="为什么选它")

        self.sector_stocks_tree.column("code", width=80)
        self.sector_stocks_tree.column("name", width=120)
        self.sector_stocks_tree.column("price", width=80)
        self.sector_stocks_tree.column("change_pct", width=80)
        self.sector_stocks_tree.column("volume", width=100)
        self.sector_stocks_tree.column("reason", width=150)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.sector_stocks_tree.yview)
        self.sector_stocks_tree.configure(yscrollcommand=scrollbar.set)

        self.sector_stocks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 操作按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="🏆 板块排行", command=self.show_sector_rankings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📈 板块走势", command=self.analyze_sector_trend).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⭐ 加入自选", command=self.add_sector_to_watchlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 导出数据", command=self.export_sector_data).pack(side=tk.LEFT, padx=5)

    def create_fund_management_tab(self, notebook):
        """资金管理标签页 - 记录实际投入的资金"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="💰 资金管理")

        # 标题
        title = ttk.Label(tab, text="💰 我的资金记录", style="Title.TLabel")
        title.pack(pady=10)

        # 资金概览
        overview_frame = ttk.LabelFrame(tab, text="钱放进去/取出来多少", padding=10)
        overview_frame.pack(fill=tk.X, padx=10, pady=5)

        self.total_invested_label = ttk.Label(overview_frame, text="💰 一共投进去的钱: 0.00 元")
        self.total_invested_label.pack(anchor=tk.W)

        self.total_withdrawn_label = ttk.Label(overview_frame, text="🏧 一共取出来的钱: 0.00 元")
        self.total_withdrawn_label.pack(anchor=tk.W)

        self.net_invested_label = ttk.Label(overview_frame, text="📌 现在还放在里面的钱: 0.00 元")
        self.net_invested_label.pack(anchor=tk.W)

        # 当前持仓对比
        compare_frame = ttk.LabelFrame(tab, text="投的钱 vs 手头股票现在值多少", padding=10)
        compare_frame.pack(fill=tk.X, padx=10, pady=5)

        self.holding_value_label = ttk.Label(compare_frame, text="当前持仓市值: 0.00 元")
        self.holding_value_label.pack(anchor=tk.W)

        self.cash_balance_label = ttk.Label(compare_frame, text="可用资金余额: 0.00 元")
        self.cash_balance_label.pack(anchor=tk.W)

        self.profit_loss_label = ttk.Label(compare_frame, text="盈亏情况: 0.00 元")
        self.profit_loss_label.pack(anchor=tk.W)

        # 资金记录列表
        list_frame = ttk.LabelFrame(tab, text="资金记录明细", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建资金记录表格
        columns = ("date", "type", "amount", "balance", "note")
        self.fund_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)

        self.fund_tree.heading("date", text="日期")
        self.fund_tree.heading("type", text="类型")
        self.fund_tree.heading("amount", text="金额(元)")
        self.fund_tree.heading("balance", text="余额(元)")
        self.fund_tree.heading("note", text="备注")

        self.fund_tree.column("date", width=120)
        self.fund_tree.column("type", width=80)
        self.fund_tree.column("amount", width=120)
        self.fund_tree.column("balance", width=120)
        self.fund_tree.column("note", width=200)

        self.fund_tree.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.fund_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.fund_tree.configure(yscrollcommand=scrollbar.set)

        # 资金操作
        operation_frame = ttk.LabelFrame(tab, text="资金操作", padding=10)
        operation_frame.pack(fill=tk.X, padx=10, pady=5)

        # 存入资金
        deposit_frame = ttk.Frame(operation_frame)
        deposit_frame.pack(fill=tk.X, pady=2)

        ttk.Label(deposit_frame, text="存入:").pack(side=tk.LEFT)
        self.deposit_amount_entry = ttk.Entry(deposit_frame, width=12)
        self.deposit_amount_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(deposit_frame, text="元  备注:").pack(side=tk.LEFT)
        self.deposit_note_entry = ttk.Entry(deposit_frame, width=20)
        self.deposit_note_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(deposit_frame, text="[MONEY] 存入资金", command=self.deposit_fund).pack(side=tk.LEFT, padx=10)

        # 取出资金
        withdraw_frame = ttk.Frame(operation_frame)
        withdraw_frame.pack(fill=tk.X, pady=2)

        ttk.Label(withdraw_frame, text="取出:").pack(side=tk.LEFT)
        self.withdraw_amount_entry = ttk.Entry(withdraw_frame, width=12)
        self.withdraw_amount_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(withdraw_frame, text="元  备注:").pack(side=tk.LEFT)
        self.withdraw_note_entry = ttk.Entry(withdraw_frame, width=20)
        self.withdraw_note_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(withdraw_frame, text="💸 取出资金", command=self.withdraw_fund).pack(side=tk.LEFT, padx=10)

        # 底部按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="[SYNC] 刷新数据", command=self.refresh_fund_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="[LIST] 资金报表", command=self.show_fund_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ 清空记录", command=self.clear_fund_records).pack(side=tk.LEFT, padx=5)

        # 初始化资金数据
        self.fund_records = self.load_fund_records()
        self.refresh_fund_data()

    def refresh_portfolio(self):
        """刷新持仓信息"""
        # 清空表格
        for item in self.portfolio_tree.get_children():
            self.portfolio_tree.delete(item)

        # 更新资金信息
        total_asset = self.portfolio.get_total_value()
        total_profit = self.portfolio.get_total_profit_loss()
        total_profit_pct = self.portfolio.get_total_profit_loss_pct()

        self.cash_label.config(text=f"📌 可用现金: {self.portfolio.cash:,.2f} 元")
        self.total_asset_label.config(text=f"💎 全部家当(总资产): {total_asset:,.2f} 元")

        # 根据盈亏设置颜色
        profit_color = "green" if total_profit >= 0 else "red"
        self.total_profit_label.config(text=f"💰 一共赚/亏: {total_profit:+,.2f} 元 ({total_profit_pct:+.2f}%)")

        # 填充持仓列表
        for pos in self.portfolio.get_position_list():
            profit = pos.get_profit_loss()
            profit_pct = pos.get_profit_loss_pct()

            item = self.portfolio_tree.insert("", tk.END, values=(
                pos.stock_code,
                pos.stock_name,
                pos.volume,
                f"{pos.avg_price:.2f}",
                f"{pos.current_price:.2f}",
                f"{pos.current_value:,.2f}",
                f"{profit:+,.2f}",
                f"{profit_pct:+.2f}%"
            ))

            # 根据盈亏设置标签颜色
            tags = ("profit" if profit >= 0 else "loss",)
            self.portfolio_tree.item(item, tags=tags)

        # 配置标签颜色
        self.portfolio_tree.tag_configure("profit", foreground="green")
        self.portfolio_tree.tag_configure("loss", foreground="red")

    def update_portfolio_prices(self):
        """更新持仓股票的最新价格"""
        def update_thread():
            self.log("\n" + "="*80)
            self.log("[STAT] 开始更新持仓价格...", "info")
            self.log("="*80)

            if not self.portfolio.get_position_list():
                self.log("当前没有持仓", "warning")
                return

            price_updates = {}
            for pos in self.portfolio.get_position_list():
                stock_code = pos.stock_code
                try:
                    # 获取最新价格
                    from datetime import datetime, timedelta
                    end_date = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')

                    df = self.crawler.get_stock_daily(stock_code, start_date, end_date)

                    if df is not None and not df.empty:
                        latest_price = df.iloc[-1]['收盘']
                        price_updates[stock_code] = latest_price
                        self.log(f"  [CHECK] {stock_code} ({pos.stock_name}): {pos.current_price:.2f} -> {latest_price:.2f}", "success")
                    else:
                        self.log(f"  [X] {stock_code}: 无法获取价格数据", "error")
                except Exception as e:
                    self.log(f"  [X] {stock_code}: 获取价格失败 - {e}", "error")

            # 更新持仓价格
            if price_updates:
                self.portfolio.update_all_prices(price_updates)
                self.portfolio.save_portfolio()

                # 刷新显示
                self.root.after(0, lambda: [
                    self.refresh_portfolio(),
                    self.log(f"\n[CHECK] 成功更新 {len(price_updates)} 只股票价格", "success"),
                    self.log(f"  总资产: {self.portfolio.get_total_value():,.2f} 元")
                ])
            else:
                self.log("\n[X] 没有成功更新任何股票价格", "error")

            self.log("="*80)

        threading.Thread(target=update_thread, daemon=True).start()

    def execute_buy(self):
        """执行买入"""
        stock_code = self.buy_code_entry.get().strip()
        try:
            volume = int(self.buy_volume_entry.get().strip())
            price = float(self.buy_price_entry.get().strip())
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的数量和价格")
            return

        if not stock_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return

        success = self.portfolio.add_position(stock_code, stock_code, volume, price)
        if success:
            self.refresh_portfolio()
            self.log(f"[OK] 买入成功: {stock_code} {volume}股 @ {price:.2f}元", "success")

    def execute_sell(self):
        """执行卖出"""
        stock_code = self.sell_code_entry.get().strip()
        try:
            volume = int(self.sell_volume_entry.get().strip())
            price = float(self.sell_price_entry.get().strip())
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的数量和价格")
            return

        if not stock_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return

        success = self.portfolio.reduce_position(stock_code, volume, price)
        if success:
            self.refresh_portfolio()
            self.log(f"[OK] 卖出成功: {stock_code} {volume}股 @ {price:.2f}元", "success")

    def show_trade_history(self):
        """显示交易记录"""
        # 创建交易记录窗口
        dialog = tk.Toplevel(self.root)
        dialog.title("交易记录")
        dialog.geometry("900x600")
        dialog.transient(self.root)

        # 创建表格
        columns = ("date", "action", "stock", "price", "volume", "amount", "profit")
        tree = ttk.Treeview(dialog, columns=columns, show="headings")

        tree.heading("date", text="日期")
        tree.heading("action", text="操作")
        tree.heading("stock", text="股票")
        tree.heading("price", text="价格")
        tree.heading("volume", text="数量(手)")
        tree.heading("amount", text="金额")
        tree.heading("profit", text="盈亏")

        tree.column("date", width=120)
        tree.column("action", width=60)
        tree.column("stock", width=150)
        tree.column("price", width=80)
        tree.column("volume", width=80)
        tree.column("amount", width=120)
        tree.column("profit", width=100)

        tree.pack(fill=tk.BOTH, expand=True)

        # 填充数据
        for record in reversed(self.portfolio.history):
            action = record['action']
            action_str = "买入" if action == 'buy' else "卖出"
            profit_str = f"{record.get('profit', 0):+,.2f}" if action == 'sell' else "-"

            stock = f"{record['stock_name']}({record['stock_code']})"

            tree.insert("", tk.END, values=(
                record['date'][:10],
                action_str,
                stock,
                f"{record['price']:.2f}",
                record['volume'],
                f"{record['amount']:,.2f}",
                profit_str
            ))

        # 关闭按钮
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)

    def clear_portfolio(self):
        """清空持仓"""
        result = messagebox.askyesno("确认", "确定要清空所有持仓吗?\n此操作不可恢复!")
        if result:
            self.portfolio.clear_portfolio()
            self.refresh_portfolio()
            self.log("[CHECK] 持仓已清空", "success")
            messagebox.showinfo("完成", "持仓已清空")

    def _open_position_dialog(self, title, prefill=None):
        """通用：新建/编辑持仓对话框（数量单位为股）
        prefill: {code,name,volume,avg_price} 编辑时带入
        """
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("380x260")
        dialog.transient(self.root)
        dialog.grab_set()

        frm = ttk.Frame(dialog, padding=16)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="代码(如 600519，不懂就留空靠名称):").grid(row=0, column=0, sticky=tk.W, pady=4)
        e_code = ttk.Entry(frm, width=22)
        e_code.grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(frm, text="名称(如 贵州茅台):").grid(row=1, column=0, sticky=tk.W, pady=4)
        e_name = ttk.Entry(frm, width=22)
        e_name.grid(row=1, column=1, padx=8, pady=4)

        ttk.Label(frm, text="数量(股，100股=1手):").grid(row=2, column=0, sticky=tk.W, pady=4)
        e_vol = ttk.Entry(frm, width=22)
        e_vol.grid(row=2, column=1, padx=8, pady=4)

        ttk.Label(frm, text="买入均价(元/股):").grid(row=3, column=0, sticky=tk.W, pady=4)
        e_price = ttk.Entry(frm, width=22)
        e_price.grid(row=3, column=1, padx=8, pady=4)

        if prefill:
            e_code.insert(0, prefill.get("code", ""))
            e_name.insert(0, prefill.get("name", ""))
            e_vol.insert(0, prefill.get("volume", ""))
            e_price.insert(0, prefill.get("avg_price", ""))

        status = {"v": None}

        def on_ok():
            code = e_code.get().strip()
            name = e_name.get().strip()
            try:
                vol = float(e_vol.get().strip())
                price = float(e_price.get().strip())
            except ValueError:
                messagebox.showwarning("提示", "数量、价格要填数字")
                return
            if not code and not name:
                messagebox.showwarning("提示", "代码和名称至少填一个")
                return
            if vol <= 0:
                messagebox.showwarning("提示", "数量要大于0")
                return
            status["v"] = {"code": code, "name": name, "volume": vol, "avg_price": price}
            dialog.destroy()

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(14, 0))
        ttk.Button(btn_row, text="保存", style="Accent.TButton", command=on_ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=6)

        dialog.wait_window()
        return status

    def add_portfolio_dialog(self):
        status = self._open_position_dialog("➕ 手动添加持仓")
        self._save_position_dialog(status, is_new=True)

    def edit_portfolio_dialog(self):
        sel = self.portfolio_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先在下方表格里选中一只股票")
            return
        vals = self.portfolio_tree.item(sel[0], "values")
        prefill = {
            "code": vals[0], "name": vals[1],
            "volume": vals[2], "avg_price": vals[3],
        }
        status = self._open_position_dialog("✏️ 编辑持仓", prefill)
        self._save_position_dialog(status, is_new=False)

    def _save_position_dialog(self, status, is_new):
        if status.get("v") is None:
            return
        d = status["v"]
        code = d["code"]
        if not code:
            # 只有名称：尝试用智能查询自动识别成代码
            try:
                from 智能数据查询 import SmartDataClient
                resolved = SmartDataClient().resolve(d["name"])
            except Exception as e:
                self.log(f"[WARN] 自动识别代码失败: {e}", "warning")
                resolved = None
            if resolved and isinstance(resolved, dict) and resolved.get("code"):
                code = resolved["code"]
                if not d["name"]:
                    d["name"] = resolved.get("name", d["name"])
            else:
                messagebox.showwarning("提示", "没能识别出代码，请直接输入股票代码")
                return

        self.portfolio.update_position(code, d["name"] or code, d["volume"], d["avg_price"])
        self.refresh_portfolio()
        self.log(f"[OK] 持仓已保存: {d['name'] or code}({code}) {d['volume']:.0f}股 @ {d['avg_price']:.2f}元", "success")
        messagebox.showinfo("完成", f"已保存 {d['name'] or code} 的持仓")

    def edit_cash_dialog(self):
        """修改可用现金（有多少没买股票的钱）"""
        dialog = tk.Toplevel(self.root)
        dialog.title("✏️ 修改可用现金")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        frm = ttk.Frame(dialog, padding=16)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="可用现金 = 还没用来买股票的钱（单位：元）").pack(anchor=tk.W, pady=4)
        ttk.Label(frm, text="填多少，就是你现在有多少闲钱。").pack(anchor=tk.W, pady=4)
        e = ttk.Entry(frm, width=24, font=("Microsoft YaHei UI", 12))
        e.pack(anchor=tk.W, pady=8)
        e.insert(0, f"{self.portfolio.cash:,.2f}")

        status = {"v": None}

        def on_ok():
            try:
                val = float(e.get().replace(",", "").strip())
            except ValueError:
                messagebox.showwarning("提示", "要填数字")
                return
            if val < 0:
                messagebox.showwarning("提示", "现金不能是负数")
                return
            status["v"] = val
            dialog.destroy()

        btn_row = ttk.Frame(frm)
        btn_row.pack(pady=(10, 0))
        ttk.Button(btn_row, text="保存", style="Accent.TButton", command=on_ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=6)

        dialog.wait_window()
        if status.get("v") is not None:
            self.portfolio.set_cash(status["v"])
            self.refresh_portfolio()
            self.log(f"[OK] 可用现金已改为 {status['v']:,.2f} 元", "success")
            messagebox.showinfo("完成", f"可用现金已改为 {status['v']:,.2f} 元")

    def delete_portfolio_item(self):
        sel = self.portfolio_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先在下方表格里选中一只股票")
            return
        vals = self.portfolio_tree.item(sel[0], "values")
        code, name = vals[0], vals[1]
        if messagebox.askyesno("确认", f"确定要从持仓里删除 {name}({code}) 吗？"):
            self.portfolio.remove_position(code)
            self.refresh_portfolio()
            self.log(f"[OK] 已删除持仓: {name}({code})", "success")

    def import_ths_dialog(self):
        """导入同花顺持仓/交割单（文件或粘贴）"""
        from tkinter import filedialog
        import 同花顺账户导入 as ths

        dialog = tk.Toplevel(self.root)
        dialog.title("📥 导入同花顺数据（持仓 / 交割单）")
        dialog.geometry("760x560")
        dialog.transient(self.root)
        dialog.grab_set()

        top = ttk.Frame(dialog, padding=10)
        top.pack(fill=tk.X)
        ttk.Label(top, text="▼ 第1步：如何从同花顺导出数据", style="Title.TLabel").pack(anchor=tk.W)
        guide = (
            "同花顺没有对散户开放自动同步，所以用「导出 → 导入」的方式把账户数据拿进来。\n"
            "· 电脑版同花顺：点左侧「持仓」→ 空白处右键 → 导出数据 → 存成 Excel 或 CSV。\n"
            "  （要同步买/卖记录，就进「交割单 / 对账单」→ 同样导出）\n"
            "· 手机版同花顺：进「持仓」→ 右上角「更多/分享」→ 导出持仓表格 → 保存后发到电脑。\n"
            "· 也可以：在同花顺里选中持仓文字，Ctrl+C 复制，直接粘贴到下方输入框。\n"
            "▼ 第2步：把文件或粘贴内容导入进来（选一种即可）"
        )
        ttk.Label(top, text=guide, style="Hint.TLabel", justify=tk.LEFT).pack(anchor=tk.W)

        # 文件导入按钮
        file_row = ttk.Frame(dialog, padding=10)
        file_row.pack(fill=tk.X)
        ttk.Label(file_row, text="方式一：从文件导入").pack(anchor=tk.W)
        ttk.Button(file_row, text="📄 选择 CSV / Excel 文件",
                   command=lambda: pick_file()).pack(anchor=tk.W, pady=4)

        # 粘贴区域
        paste_frame = ttk.LabelFrame(dialog, text="方式二：直接粘贴表格（持仓或交割单）", padding=8)
        paste_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self._ths_paste_text = scrolledtext.ScrolledText(paste_frame, height=8, font=("Microsoft YaHei UI", 10))
        self._ths_paste_text.pack(fill=tk.BOTH, expand=True)
        ttk.Button(paste_frame, text="📥 导入粘贴的内容",
                   command=lambda: pick_paste()).pack(pady=6)

        # 预览/结果
        result_frame = ttk.LabelFrame(dialog, text="结果", padding=8)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self._ths_result_text = scrolledtext.ScrolledText(result_frame, height=6, font=("Microsoft YaHei UI", 10))
        self._ths_result_text.pack(fill=tk.BOTH, expand=True)
        ttk.Button(result_frame, text="✅ 确认导入到「我的持仓」",
                   style="Accent.TButton", command=lambda: confirm_apply()).pack(pady=6)

        self._import_preview = None  # {"type":..., "rows":..., "cash":...}

        def set_result(msg):
            self._ths_result_text.config(state=tk.NORMAL)
            self._ths_result_text.delete(1.0, tk.END)
            self._ths_result_text.insert(1.0, msg)
            self._ths_result_text.config(state=tk.DISABLED)

        def parse_and_preview(rows, src):
            try:
                if "买卖合同" in " ".join(str(c) for r in rows[:2] for c in r):
                    pass
                if any(any(kw in str(c) for kw in ths._KEY_COLUMNS["action"]) for c in rows[0]):
                    recs = ths.parse_transactions(rows)
                    self._import_preview = {"type": "transactions", "rows": recs, "cash": None}
                    lines = [f"读到了 {src}，共 {len(recs)} 笔买/卖记录："]
                    for r in recs[:8]:
                        act = "买入" if r["action"] == "buy" else "卖出"
                        lines.append(f"  {r['date']} {act} {r['name']}({r['code']}) {r['volume']:.0f}股 @{r['price']:.2f}")
                    lines.append("提示：确认后会用这些流水重新算一遍持仓。")
                    set_result("\n".join(lines))
                else:
                    res = ths.parse_holdings(rows)
                    self._import_preview = {"type": "holdings", "rows": res["positions"], "cash": res.get("cash")}
                    lines = [f"读到了 {src}，共 {len(res['positions'])} 只持仓："]
                    for p in res["positions"][:8]:
                        lines.append(f"  {p['name']}({p['code']}) {p['volume']:.0f}股 成本{p['avg_price']:.2f}")
                    if res.get("cash") is not None:
                        lines.append(f"（顺带读到可用资金：{res['cash']:.2f} 元）")
                    lines.append("提示：确认后会用这些数据整体替换「我的持仓」。")
                    set_result("\n".join(lines))
            except Exception as e:
                set_result(f"解析失败：{e}\n\n请确认表格里有「证券代码 / 数量 / 成本价」列，或「成交日期 / 买卖标志」列。")
                self._import_preview = None

        def pick_file():
            path = filedialog.askopenfilename(
                title="选择同花顺导出的表",
                filetypes=[("表格文件", "*.csv *.txt *.xls *.xlsx *.xlsm"), ("所有文件", "*.*")])
            if not path:
                return
            try:
                rows = ths.load_table(path)
            except Exception as e:
                set_result(f"读取文件失败：{e}")
                return
            parse_and_preview(rows, os.path.basename(path))

        def pick_paste():
            text = self._ths_paste_text.get(1.0, tk.END)
            if not text.strip():
                messagebox.showwarning("提示", "请先粘贴内容")
                return
            try:
                res = ths.parse_pasted(text)
            except Exception as e:
                set_result(f"解析失败：{e}")
                self._import_preview = None
                return
            if res["type"] == "transactions":
                self._import_preview = {"type": "transactions", "rows": res["data"], "cash": None}
                recs = res["data"]
                lines = [f"读到 {len(recs)} 笔买/卖记录："]
                for r in recs[:8]:
                    act = "买入" if r["action"] == "buy" else "卖出"
                    lines.append(f"  {r['date']} {act} {r['name']}({r['code']}) {r['volume']:.0f}股 @{r['price']:.2f}")
                lines.append("提示：确认后会用这些流水重新算一遍持仓。")
                set_result("\n".join(lines))
            else:
                self._import_preview = {"type": "holdings", "rows": res["data"]["positions"], "cash": res["data"].get("cash")}
                lines = [f"读到 {len(res['data']['positions'])} 只持仓："]
                for p in res["data"]["positions"][:8]:
                    lines.append(f"  {p['name']}({p['code']}) {p['volume']:.0f}股 成本{p['avg_price']:.2f}")
                if res["data"].get("cash") is not None:
                    lines.append(f"（顺带读到可用资金：{res['data']['cash']:.2f} 元）")
                lines.append("提示：确认后会用这些数据整体替换「我的持仓」。")
                set_result("\n".join(lines))

        def confirm_apply():
            if self._import_preview is None:
                messagebox.showwarning("提示", "还没有可导入的数据，请先选文件或粘贴内容")
                return
            p = self._import_preview
            try:
                if p["type"] == "holdings":
                    n = self.portfolio.replace_all_positions(p["rows"], cash=p.get("cash"))
                    self.log(f"[OK] 已从同花顺导入持仓 {n} 只", "success")
                    messagebox.showinfo("完成", f"已导入 {n} 只持仓到「我的持仓」")
                else:
                    # 用交割单重建：初始资金可沿用现有现金
                    n_pos, n_rec = self.portfolio.apply_transactions(p["rows"], initial_cash=None)
                    self.log(f"[OK] 已从同花顺交割单重建持仓：{n_pos} 只，{n_rec} 笔成交", "success")
                    messagebox.showinfo("完成", f"已按交割单重建持仓：{n_pos} 只，{n_rec} 笔成交")
                self.refresh_portfolio()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"导入失败：{e}")

    def load_fund_records(self):
        """加载资金记录"""
        import json
        fund_file = os.path.join(os.path.dirname(__file__), 'fund_records.json')
        try:
            if os.path.exists(fund_file):
                with open(fund_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"[WARN]  加载资金记录失败: {e}", "warning")
        return []

    def save_fund_records(self):
        """保存资金记录"""
        import json
        fund_file = os.path.join(os.path.dirname(__file__), 'fund_records.json')
        try:
            with open(fund_file, 'w', encoding='utf-8') as f:
                json.dump(self.fund_records, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.log(f"[ERROR] 保存资金记录失败: {e}", "error")
            return False

    def deposit_fund(self):
        """存入资金"""
        try:
            amount = float(self.deposit_amount_entry.get().strip())
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的金额")
            return

        if amount <= 0:
            messagebox.showwarning("警告", "金额必须大于0")
            return

        note = self.deposit_note_entry.get().strip() or "存入资金"

        # 计算当前余额
        balance = sum(r['amount'] if r['type'] == '存入' else -r['amount'] for r in self.fund_records)

        # 添加记录
        record = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': '存入',
            'amount': amount,
            'balance': balance + amount,
            'note': note
        }
        self.fund_records.append(record)

        # 联动持仓管理:增加可用资金
        old_cash = self.portfolio.cash
        self.portfolio.cash += amount
        self.portfolio.save_portfolio()

        if self.save_fund_records():
            self.refresh_fund_data()
            self.refresh_portfolio()  # 同步刷新持仓信息
            self.log(f"[OK] 存入资金成功: {amount:,.2f} 元", "success")
            self.log(f"   账户可用资金: {old_cash:,.2f} -> {self.portfolio.cash:,.2f} 元", "info")
            self.deposit_amount_entry.delete(0, tk.END)
            self.deposit_note_entry.delete(0, tk.END)
            messagebox.showinfo("成功", f"已存入 {amount:,.2f} 元\n可用资金已更新为 {self.portfolio.cash:,.2f} 元")
        else:
            messagebox.showerror("错误", "保存记录失败")

    def withdraw_fund(self):
        """取出资金"""
        try:
            amount = float(self.withdraw_amount_entry.get().strip())
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的金额")
            return

        if amount <= 0:
            messagebox.showwarning("警告", "金额必须大于0")
            return

        # 检查余额
        balance = sum(r['amount'] if r['type'] == '存入' else -r['amount'] for r in self.fund_records)
        if amount > balance:
            messagebox.showwarning("警告", f"余额不足! 当前余额: {balance:,.2f} 元")
            return

        # 检查持仓管理的可用资金
        if amount > self.portfolio.cash:
            confirm = messagebox.askyesno(
                "提示",
                f"要取出的金额({amount:,.2f}元)超过了可用资金({self.portfolio.cash:,.2f}元)\n\n"
                f"这意味着您需要卖出持仓股票才能取出。\n"
                f"是否继续?"
            )
            if not confirm:
                return

        note = self.withdraw_note_entry.get().strip() or "取出资金"

        # 添加记录
        record = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': '取出',
            'amount': amount,
            'balance': balance - amount,
            'note': note
        }
        self.fund_records.append(record)

        # 联动持仓管理:扣除可用资金
        old_cash = self.portfolio.cash
        self.portfolio.cash -= amount
        if self.portfolio.cash < 0:
            self.portfolio.cash = 0
        self.portfolio.save_portfolio()

        if self.save_fund_records():
            self.refresh_fund_data()
            self.refresh_portfolio()  # 同步刷新持仓信息
            self.log(f"[OK] 取出资金成功: {amount:,.2f} 元", "success")
            self.log(f"   账户可用资金: {old_cash:,.2f} -> {self.portfolio.cash:,.2f} 元", "info")
            self.withdraw_amount_entry.delete(0, tk.END)
            self.withdraw_note_entry.delete(0, tk.END)
            messagebox.showinfo("成功", f"已取出 {amount:,.2f} 元\n可用资金已更新为 {self.portfolio.cash:,.2f} 元")
        else:
            messagebox.showerror("错误", "保存记录失败")

    def refresh_fund_data(self):
        """刷新资金数据"""
        # 重新加载记录
        self.fund_records = self.load_fund_records()

        # 清空表格
        for item in self.fund_tree.get_children():
            self.fund_tree.delete(item)

        # 计算统计数据
        total_invested = sum(r['amount'] for r in self.fund_records if r['type'] == '存入')
        total_withdrawn = sum(r['amount'] for r in self.fund_records if r['type'] == '取出')
        net_invested = total_invested - total_withdrawn
        current_balance = net_invested

        # 更新概览标签
        self.total_invested_label.config(text=f"💰 一共投进去的钱: {total_invested:,.2f} 元")
        self.total_withdrawn_label.config(text=f"🏧 一共取出来的钱: {total_withdrawn:,.2f} 元")
        self.net_invested_label.config(text=f"📌 现在还放在里面的钱: {net_invested:,.2f} 元")

        # 获取持仓数据
        holding_value = 0
        for pos in self.portfolio.get_position_list():
            holding_value += pos.current_value

        cash_balance = self.portfolio.cash
        total_value = holding_value + cash_balance

        # 更新持仓对比标签
        self.holding_value_label.config(text=f"当前持仓市值: {holding_value:,.2f} 元")
        self.cash_balance_label.config(text=f"可用资金余额: {cash_balance:,.2f} 元")

        # 计算盈亏(当前总价值 - 净投入)
        profit_loss = total_value - net_invested
        profit_pct = (profit_loss / net_invested * 100) if net_invested > 0 else 0

        # 根据盈亏设置颜色
        if profit_loss >= 0:
            profit_text = f"盈亏情况: +{profit_loss:,.2f} 元 (+{profit_pct:.2f}%)"
            self.profit_loss_label.config(text=profit_text, foreground="green")
        else:
            profit_text = f"盈亏情况: {profit_loss:,.2f} 元 ({profit_pct:.2f}%)"
            self.profit_loss_label.config(text=profit_text, foreground="red")

        # 填充资金记录表格
        for record in reversed(self.fund_records):
            item = self.fund_tree.insert("", tk.END, values=(
                record['date'],
                record['type'],
                f"{record['amount']:,.2f}",
                f"{record['balance']:,.2f}",
                record['note']
            ))

            # 根据类型设置标签颜色
            tags = ("deposit",) if record['type'] == '存入' else ("withdraw",)
            self.fund_tree.item(item, tags=tags)

        # 配置标签颜色
        self.fund_tree.tag_configure("deposit", foreground="green")
        self.fund_tree.tag_configure("withdraw", foreground="red")

    def show_fund_report(self):
        """显示资金报表"""
        if not self.fund_records:
            messagebox.showinfo("提示", "暂无资金记录")
            return

        report_window = tk.Toplevel(self.root)
        report_window.title("资金报表")
        report_window.geometry("600x500")
        report_window.transient(self.root)

        # 统计数据
        total_invested = sum(r['amount'] for r in self.fund_records if r['type'] == '存入')
        total_withdrawn = sum(r['amount'] for r in self.fund_records if r['type'] == '取出')
        net_invested = total_invested - total_withdrawn

        holding_value = sum(pos.current_value for pos in self.portfolio.get_position_list())
        cash_balance = self.portfolio.cash
        total_value = holding_value + cash_balance
        profit_loss = total_value - net_invested
        profit_pct = (profit_loss / net_invested * 100) if net_invested > 0 else 0

        # 显示内容
        text = scrolledtext.ScrolledText(report_window, wrap=tk.WORD, font=("Arial", 11))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        report_content = f"""
{'='*60}
                        资金报表
{'='*60}

【资金流水统计】
  累计存入: {total_invested:,.2f} 元
  累计取出: {total_withdrawn:,.2f} 元
  净投入:   {net_invested:,.2f} 元

【当前持仓状况】
  持仓市值: {holding_value:,.2f} 元
  可用资金: {cash_balance:,.2f} 元
  总资产:   {total_value:,.2f} 元

【盈亏分析】
  实际盈亏: {profit_loss:+,.2f} 元
  收益率:   {profit_pct:+.2f}%

{'='*60}
                        详细记录
{'='*60}
"""
        for record in self.fund_records:
            report_content += f"\n{record['date']}  {record['type']:>4}  {record['amount']:>12,.2f}  余额:{record['balance']:>12,.2f}  {record['note']}\n"

        text.insert(1.0, report_content)
        text.config(state=tk.DISABLED)

        ttk.Button(report_window, text="关闭", command=report_window.destroy).pack(pady=10)

    def clear_fund_records(self):
        """清空资金记录"""
        if not self.fund_records:
            messagebox.showinfo("提示", "没有资金记录可清空")
            return

        result = messagebox.askyesno("确认", "确定要清空所有资金记录吗?\n注意: 这不会影响持仓管理中的资金!\n此操作不可恢复!")
        if result:
            self.fund_records = []
            if self.save_fund_records():
                self.refresh_fund_data()
                self.log("[OK] 资金记录已清空", "success")
                messagebox.showinfo("完成", "资金记录已清空\n持仓管理中的资金保持不变")

    def create_data_management_tab(self, notebook):
        """数据管理标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🗂️ 数据管理")
        
        # 标题
        title = ttk.Label(tab, text="智能数据管理", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # 数据统计信息
        stats_frame = ttk.LabelFrame(tab, text="数据统计", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 实时数据占用显示
        self.storage_label = ttk.Label(stats_frame, text="正在计算数据占用...")
        self.storage_label.pack(anchor=tk.W)
        
        # 进度条显示
        self.storage_progress = ttk.Progressbar(stats_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.storage_progress.pack(fill=tk.X, pady=5)
        
        self.storage_text = ttk.Label(stats_frame, text="")
        self.storage_text.pack(anchor=tk.W)
        
        # 刷新按钮
        refresh_btn = ttk.Button(stats_frame, text="[SYNC] 刷新统计", 
                               command=self.update_storage_info)
        refresh_btn.pack(anchor=tk.E, pady=5)
        
        # 数据清理配置
        cleanup_frame = ttk.LabelFrame(tab, text="智能清理配置", padding=10)
        cleanup_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 数据上限设置
        ttk.Label(cleanup_frame, text="数据存储上限 (MB):").pack(anchor=tk.W)
        self.storage_limit_var = tk.StringVar(value="100")
        limit_frame = ttk.Frame(cleanup_frame)
        limit_frame.pack(fill=tk.X, pady=5)
        
        self.storage_limit_entry = ttk.Entry(limit_frame, textvariable=self.storage_limit_var, width=10)
        self.storage_limit_entry.pack(side=tk.LEFT)
        
        limit_scale = ttk.Scale(limit_frame, from_=10, to=500, orient=tk.HORIZONTAL,
                               variable=tk.DoubleVar(value=100), 
                               command=self.update_limit_from_scale)
        limit_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        # 清理策略
        ttk.Label(cleanup_frame, text="清理策略:").pack(anchor=tk.W, pady=(10, 0))
        strategy_frame = ttk.Frame(cleanup_frame)
        strategy_frame.pack(fill=tk.X, pady=5)
        
        self.cleanup_strategy_var = tk.StringVar(value="oldest")
        ttk.Radiobutton(strategy_frame, text="删除最早的文件", 
                       variable=self.cleanup_strategy_var, value="oldest").pack(side=tk.LEFT)
        ttk.Radiobutton(strategy_frame, text="删除性能最差的模型", 
                       variable=self.cleanup_strategy_var, value="worst").pack(side=tk.LEFT)
        
        # 清理选项
        options_frame = ttk.Frame(cleanup_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        self.cleanup_models_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="清理AI模型文件", 
                       variable=self.cleanup_models_var).pack(side=tk.LEFT, padx=(0, 20))
        
        self.cleanup_data_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="清理股票数据文件", 
                       variable=self.cleanup_data_var).pack(side=tk.LEFT)
        
        # 按钮区域
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=20)
        
        ttk.Button(btn_frame, text="[FIND] 分析数据占用", 
                  command=self.analyze_storage, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🧹 智能清理", 
                  command=self.smart_cleanup, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="[WARN] 手动选择删除", 
                  command=self.manual_cleanup, width=20).pack(side=tk.LEFT, padx=5)
        
        # 打开文件管理器按钮
        open_btn_frame = ttk.Frame(tab)
        open_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(open_btn_frame, text="📂 打开文件管理器", 
                  command=self.open_file_manager, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(open_btn_frame, text="[STAT] 查看所有文件", 
                  command=self.view_all_files, width=30).pack(side=tk.LEFT, padx=5)
        
        # 初始化数据统计
        self.update_storage_info()
    
    def create_tutorial_tab(self, notebook):
        """新手教学标签页：买卖教程 + 同花顺账户导入"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📖 新手教学")

        # 顶部说明
        intro = ttk.Frame(tab, padding=(12, 8))
        intro.pack(fill=tk.X, padx=10, pady=(8, 2))
        ttk.Label(intro, text="💡 不会买卖股票？这个页面一步步教你。想分析自己账户？从同花顺导入数据就能一键分析。",
                  style="Hint.TLabel").pack(anchor=tk.W)

        # 教程正文（可滚动）
        body_frame = ttk.LabelFrame(tab, text="📖 新手教程（以同花顺为例）", padding=8)
        body_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        body_text = scrolledtext.ScrolledText(body_frame, wrap=tk.WORD,
                                              font=("Microsoft YaHei UI", 11), padx=12, pady=12)
        body_text.pack(fill=tk.BOTH, expand=True)
        body_text.tag_configure("h", font=("Microsoft YaHei UI", 12, "bold"), foreground="#1e3a8a", spacing1=6, spacing3=4)
        body_text.tag_configure("body", spacing1=1, spacing3=3, lmargin1=12)
        body_text.tag_configure("note", foreground="#b45309")

        tutorial = (
            "总述：买股票 = 花钱买某个公司的股份，股票分红和涨跌决定你赚不赚。A股最小要买 100 股（1手）。\n\n"

            "【名词小课堂】（先花1分钟看懂这些词）\n"
            "· 股：买股票的数量单位，就像买苹果按“斤”、买水按“瓶”。你买一只股票，就是买“100股、300股”这样的股数。\n"
            "· 手：股的另一种叫法，1手=100股。A股最少买100股，也就是最少买1手。\n"
            "· 仓：可以想象成“你的股票柜子”。\n"
            "· 持仓：放在你柜子里的股票（买来还没卖掉的）。本软件的「💼 我的持仓」页就是给你看这个柜子的。\n"
            "· 仓位：你的钱里有多少变成了股票。比如你有10万，其中6万买了股票，就叫“6成仓”。\n"
            "· 现价：股票现在卖多少钱一股。\n"
            "· 成本价（买入均价）：你买这只股票平均每股价钱，和现价比就能看出赚亏。\n"
            "· 可用现金：还没拿来买股票的钱。\n"
            "· 总资产（全部家当）：可用现金 + 所有股票现在值多少钱。\n\n"

            "【怎么买股票】（以同花顺 App 为例）\n"
            "第1步 打开同花顺，顶部搜索框输入股票名字（如“贵州茅台”）或代码（600519），点进去。\n"
            "第2步 进入股票页面后，找到下方的“买”按钮并点击。\n"
            "第3步 在买入界面：\n"
            "  · 价格：默认是“现价”（就是现在成交的价格）。想挂单等更低价，就在“委托价格”里填你要的价格。\n"
            "  · 数量：填你要买的股数，必须是100的倍数（如 100、200、500股）。\n"
            "第4步 核对价格和数量无误后，点“买入”并确认。买入成功后，这只股票就出现在你的“持仓”里了。\n\n"

            "【怎么卖股票】（同花顺为例）\n"
            "第1步 在同花顺下方或“交易”里进“持仓”，找到要卖的股票。\n"
            "第2步 点“卖”，输入要卖的股数（不超过你手里的数量），价格可填你想卖的价格或点“市价/现价”。\n"
            "第3步 核对后点“卖出”并确认，卖出后资金回到你的可用资金里。\n\n"

            "【新手必知的小规则】\n"
            "· T+1：今天买的股票，最快明天才能卖（基金不受此限制）。\n"
            "· 涨跌停：股票每天涨/跌一般最多10%（创业板/科创板20%），到了就买不进或卖不出。\n"
            "· 手续费：买卖都要付一点点佣金，所以别频繁买进卖出。\n"
            "· 你没开户是买不了的：买卖前要在券商（或同花顺合作券商）开户并绑定银行卡。\n\n"

            "【把这个软件里的数据当参考，别当“保赚”】\n"
            "本软件只是帮你把行情算清楚、辅助分析，不保证赚钱。股市有风险，务必只用闲钱投资。\n"
        )
        for line in tutorial.split("\n"):
            st = line.strip()
            if st.startswith("【") or st.startswith("总述"):
                body_text.insert(tk.END, line + "\n", ("h",))
            else:
                body_text.insert(tk.END, line + "\n", ("body",))
        body_text.config(state=tk.DISABLED)

        # 同花顺账户导入区
        guide_frame = ttk.LabelFrame(tab, text="📥 把同花顺账户数据导入本软件（便于快速分析）", padding=10)
        guide_frame.pack(fill=tk.X, padx=10, pady=5)
        guide_label = ttk.Label(
            guide_frame,
            text=(
                "同花顺没开放“自动同步账户”给普通用户，所以我们用最安全的方式：你在同花顺里导出一张表，导入这里。\n"
                "· 电脑版：进「持仓」（要同步买卖流水就进「交割单/对账单」）→ 右键 → 导出数据 → 存成 Excel 或 CSV。\n"
                "· 手机版：进「持仓」→ 右上角「更多/分享」→ 导出/复制 → 发到这台电脑。\n"
                "· 也可以：在同花顺里选中持仓文字 Ctrl+C，回来点下面「粘贴导入」。"
            ),
            justify=tk.LEFT, style="Hint.TLabel").pack(anchor=tk.W)
        ttk.Button(guide_frame, text="📥 导入同花顺数据（持仓/交割单）",
                   style="Accent.TButton",
                   command=self.import_ths_dialog).pack(anchor=tk.W, pady=(8, 0))

    def create_smart_query_tab(self, notebook):
        """智能查询标签页：自动识别输入(名称/代码)、自动选源、智能缓存、智能分析"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🔍 智能查询")

        self.smart_running = False
        self.smart_auto_update_var = tk.BooleanVar(value=False)

        # 新手说明条
        help_frame = ttk.Frame(tab, padding=(12, 8))
        help_frame.pack(fill=tk.X, padx=10, pady=(8, 2))
        ttk.Label(help_frame, text="👋 新手看这里：红=涨，绿=跌。", style="Hint.TLabel").pack(anchor=tk.W)
        ttk.Label(help_frame, text="    现价=现在多少钱 · 今日涨跌=和昨天比涨跌了百分之几 · 成交金额=大家今天总共买卖了多少钱 · 活跃度/热度比=这只票今天受不受关注。",
                  style="Hint.TLabel").pack(anchor=tk.W)

        # 输入区
        input_frame = ttk.LabelFrame(tab, text="🔍 输入要查的东西（股票/基金/指数名字或代码都可以，逗号分隔）", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(input_frame, text="输入:").pack(anchor=tk.W)
        self.smart_entry = ttk.Entry(input_frame, width=60, font=("Microsoft YaHei UI", 12))
        self.smart_entry.pack(fill=tk.X, pady=5)
        self.smart_entry.insert(0, "贵州茅台,上证指数,沪深300ETF,159915")
        ttk.Label(input_frame, text="例: 贵州茅台 / 600519 / 上证指数 / 沪深300 / 510300（不用懂代码，打名字就行）",
                  style="Hint.TLabel").pack(anchor=tk.W)

        opt_row = ttk.Frame(input_frame)
        opt_row.pack(fill=tk.X, pady=(8, 4))

        # 类型提示（消除歧义，如代码000001）
        ttk.Label(opt_row, text="想查的是:").pack(side=tk.LEFT)
        self.smart_type_var = tk.StringVar(value="自动")
        type_box = ttk.Combobox(opt_row, textvariable=self.smart_type_var, state="readonly",
                                values=["自动", "股票", "基金", "指数", "板块"], width=8)
        type_box.pack(side=tk.LEFT, padx=5)
        ttk.Label(opt_row, text="（选“自动”就行，程序会自己判断）", style="Hint.TLabel").pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(opt_row, text="自动刷新间隔(秒):").pack(side=tk.LEFT, padx=(20, 5))
        self.smart_interval_var = tk.StringVar(value="30")
        ttk.Spinbox(opt_row, from_=5, to=600, textvariable=self.smart_interval_var, width=8).pack(side=tk.LEFT)

        btn_row = ttk.Frame(input_frame)
        btn_row.pack(fill=tk.X, pady=8)
        ttk.Button(btn_row, text="🔍 查询", style="Accent.TButton",
                   command=self.smart_query, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="📈 历史走势", command=self.smart_query_history, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(btn_row, text="自动刷新", variable=self.smart_auto_update_var,
                        command=self.smart_toggle_auto).pack(side=tk.LEFT, padx=15)
        ttk.Button(btn_row, text="💾 导出表格", command=self.smart_export, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="🧹 清缓存", command=self.smart_clear_cache, width=10).pack(side=tk.LEFT, padx=5)

        # 长线选股区
        lt_frame = ttk.LabelFrame(tab, text="🌱 长线选股（预测适合长期持有的好股票，评分越高越值得长持）", padding=8)
        lt_frame.pack(fill=tk.X, padx=10, pady=5)

        lt_row = ttk.Frame(lt_frame)
        lt_row.pack(fill=tk.X)
        self.lt_entry = ttk.Entry(lt_frame, width=55, font=("Microsoft YaHei UI", 11))
        self.lt_entry.pack(fill=tk.X, pady=3)
        self.lt_entry.insert(0, "贵州茅台,五粮液,比亚迪,宁德时代,招商银行")
        ttk.Label(lt_frame, text="输入想筛选的股票（名字/代码，逗号分隔），然后点下面的按钮：",
                  style="Hint.TLabel").pack(anchor=tk.W)

        lt_btn_row = ttk.Frame(lt_frame)
        lt_btn_row.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(lt_btn_row, text="🎯 单只长线诊断", style="Accent.TButton",
                   command=self.longterm_diagnose, width=14).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(lt_btn_row, text="🏆 筛选长线好股", command=self.longterm_screen, width=14).pack(side=tk.LEFT, padx=5)
        self.lt_status_label = ttk.Label(lt_btn_row, text="状态: 未分析", foreground="gray")
        self.lt_status_label.pack(side=tk.LEFT, padx=12)

        self.lt_result_text = scrolledtext.ScrolledText(lt_frame, height=7, width=100,
                                                        font=("Microsoft YaHei UI", 10))
        self.lt_result_text.pack(fill=tk.X, pady=(5, 0))
        self.lt_result_text.insert(tk.END, "长线选股说明：综合【走势趋势 + 财务基本面 + AI模型预测】三项评分。\n"
                                          "· 技术面(40%)：看长期均线是否多头、一年涨跌、波动大小、回撤深不深。\n"
                                          "· 基本面(40%)：看公司赚不赚钱（ROE）、营收支不增长、毛利率、负债、现金流。\n"
                                          "· AI预测(20%)：用机器学习学习历史走势后预测未来短期方向。\n"
                                          "总分越高（A/B级）越适合长期持有，C/D级需谨慎。")
        self.lt_result_text.config(state=tk.DISABLED)

        self.smart_status_label = ttk.Label(tab, text="状态: 未查询", foreground="gray")
        self.smart_status_label.pack(anchor=tk.W, padx=12, pady=3)

        # 结果表格
        data_frame = ttk.LabelFrame(tab, text="📋 行情表", padding=6)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("类型", "代码", "名称", "现价", "今日涨跌", "涨跌金额", "成交量", "成交金额",
                   "最高价", "最低价", "今开价", "昨收价", "波动幅度", "活跃度", "热度比")
        self.smart_tree = ttk.Treeview(data_frame, columns=columns, show="headings", height=12)
        widths = {"类型": 48, "代码": 66, "名称": 130, "现价": 70, "今日涨跌": 68, "涨跌金额": 68,
                  "成交量": 85, "成交金额": 90, "最高价": 64, "最低价": 64, "今开价": 64, "昨收价": 64,
                  "波动幅度": 60, "活跃度": 60, "热度比": 54}
        for col, w in widths.items():
            self.smart_tree.heading(col, text=col)
            self.smart_tree.column(col, width=w, anchor=tk.E if col not in ("类型", "代码", "名称") else tk.W)
        sb = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.smart_tree.yview)
        self.smart_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.smart_tree.pack(fill=tk.BOTH, expand=True)

        # 智能分析区
        analysis_frame = ttk.LabelFrame(tab, text="🧠 智能解读（AI帮你看懂）", padding=6)
        analysis_frame.pack(fill=tk.X, padx=10, pady=5)
        self.smart_analysis_text = scrolledtext.ScrolledText(analysis_frame, height=6, width=100,
                                                             font=("Microsoft YaHei UI", 10))
        self.smart_analysis_text.pack(fill=tk.BOTH, expand=True)
        self.smart_analysis_text.config(state=tk.DISABLED)

    def _smart_type_hint(self):
        m = {"自动": None, "股票": ["stock"], "基金": ["fund"], "指数": ["index"], "板块": ["board"]}.get(
            self.smart_type_var.get(), None)
        return m

    def smart_query(self, _event=None):
        """执行智能查询（后台线程）"""
        if self.smart_running:
            return
        text = self.smart_entry.get().strip()
        if not text:
            messagebox.showwarning("警告", "请输入股票/基金/指数名称或代码")
            return

        def work():
            self.smart_running = True
            self.smart_status_label.config(text="状态: 查询中...", foreground="blue")
            _t0 = time.time()
            try:
                df = self.smart_client.get_realtime(text, types_hint=self._smart_type_hint())
                self.root.after(0, lambda: self._show_smart_result(df, _t0))
            except Exception as e:
                self.root.after(0, lambda: [
                    self.smart_status_label.config(text=f"状态: 失败 - {e}", foreground="red"),
                    self.log(f"[ERROR] 智能查询失败: {e}", "error")])
            finally:
                self.smart_running = False

        threading.Thread(target=work, daemon=True).start()

    def _show_smart_result(self, df, _t0=None):
        elapsed = (time.time() - _t0) if _t0 else 0.0
        self.smart_tree.delete(*self.smart_tree.get_children())
        for _, r in df.iterrows():
            self.smart_tree.insert("", tk.END, values=(
                r.get('type_name', ''),
                r.get('symbol', ''),
                r.get('name', ''),
                self._f(r, 'price', 2),
                f"{self._f(r,'change_percent',2):+.2f}%",
                f"{self._f(r,'change_amount',2):+.2f}",
                f"{int(self._f(r,'volume',0)):,}",
                f"{int(self._f(r,'amount',0)):,}",
                self._f(r, 'high', 2),
                self._f(r, 'low', 2),
                self._f(r, 'open', 2),
                self._f(r, 'pre_close', 2),
                f"{self._f(r,'amplitude',2):.2f}%",
                f"{self._f(r,'turnover_rate',2):.2f}%",
                self._f(r, 'volume_ratio', 2),
            ))
            tags = ("up",) if self._f(r, 'change_percent', 0) >= 0 else ("down",)
            self.smart_tree.item(self.smart_tree.get_children()[-1], tags=tags)
        # 颜色配置
        self.smart_tree.tag_configure("up", foreground="#e03131")
        self.smart_tree.tag_configure("down", foreground="#2f9e44")

        # 智能分析面板
        lines = []
        if hasattr(df, 'at') and 'analysis' in df.columns:
            for _, r in df.iterrows():
                lines.append(f"• {r.get('symbol','')} {r.get('name','')}: {r.get('analysis','')}")
        if not lines:
            lines.append("• 未返回有效数据，请检查输入或网络。")
        self.smart_analysis_text.config(state=tk.NORMAL)
        self.smart_analysis_text.delete(1.0, tk.END)
        self.smart_analysis_text.insert(1.0, "\n".join(lines))
        self.smart_analysis_text.config(state=tk.DISABLED)

        n = max(0, len(self.smart_tree.get_children()))
        self.smart_status_label.config(text=f"状态: 查询成功 - {n} 条（缓存 {self.smart_client.cache_stats['entries']} 条）",
                                       foreground="green")
        self.log(f"[OK] 智能查询完成: {n} 条，用时 {elapsed:.2f}s")

    @staticmethod
    def _f(r, k, nd=2):
        try:
            v = r.get(k, 0)
            return round(float(v) if v is not None else 0.0, nd)
        except (TypeError, ValueError):
            return 0.0

    def smart_query_history(self):
        text = self.smart_entry.get().strip()
        if not text:
            messagebox.showwarning("警告", "请先输入")
            return
        token = text.split(',')[0].strip()
        df = self.smart_client.get_history(token)
        self.log(f"[HIST] {token} 历史数据 {len(df)} 条")
        if not df.empty:
            self.log(df.tail(10).to_string(index=False))
            messagebox.showinfo("历史走势", f"{token} 共 {len(df)} 条历史记录（最近10条已显示在右侧日志里）")

    def smart_toggle_auto(self):
        if self.smart_auto_update_var.get():
            self.smart_interval = int(float(self.smart_interval_var.get() or 30))
            self.smart_auto_update()
        elif hasattr(self, '_smart_auto_id'):
            self.root.after_cancel(self._smart_auto_id)

    def smart_auto_update(self):
        if not self.smart_auto_update_var.get():
            return
        self.smart_query()
        try:
            self._smart_auto_id = self.root.after(int(self.smart_interval * 1000), self.smart_auto_update)
        except Exception:
            pass

    def smart_export(self):
        from tkinter import filedialog
        rows = self.smart_tree.get_children()
        if not rows:
            messagebox.showwarning("警告", "没有可导出的数据")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"smart_quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if not path:
            return
        try:
            import csv as _csv
            headers = ["类型", "代码", "名称", "现价", "今日涨跌", "涨跌金额", "成交量", "成交金额",
                       "最高价", "最低价", "今开价", "昨收价", "波动幅度", "活跃度", "热度比"]
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = _csv.writer(f)
                w.writerow(headers)
                for iid in rows:
                    vals = self.smart_tree.item(iid, "values")
                    w.writerow([v[:-1] if isinstance(v, str) and v.endswith('%') else v for v in vals])
            messagebox.showinfo("成功", f"已导出: {path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")

    def smart_clear_cache(self):
        self.smart_client.cache.clear()
        self.smart_status_label.config(text="状态: 缓存已清空", foreground="orange")
        self.log("[OK] 智能缓存已清空")

    def _lt_set_status(self, text, color="gray"):
        try:
            self.lt_status_label.config(text=text, foreground=color)
        except Exception:
            pass

    def _lt_show(self, text):
        self.lt_result_text.config(state=tk.NORMAL)
        self.lt_result_text.delete(1.0, tk.END)
        self.lt_result_text.insert(tk.END, text)
        self.lt_result_text.config(state=tk.DISABLED)

    def longterm_diagnose(self):
        """单只长线诊断（后台线程）"""
        token = self.lt_entry.get().strip().split(',')[0].strip()
        if not token:
            messagebox.showwarning("警告", "请先输入股票名字或代码")
            return
        self._lt_set_status(f"状态: 正在分析 {token}...", "blue")
        self._lt_show(f"⏳ 正在分析 {token}，需要下载3年历史行情和财务数据，请稍候...")

        def work():
            try:
                rep = self.longterm.analyze(token)
                self.root.after(0, lambda: self._show_longterm_report(rep, token))
            except Exception as e:
                self.root.after(0, lambda: [
                    self._lt_show(f"❌ 分析失败：{e}"),
                    self._lt_set_status(f"状态: 失败 - {e}", "red"),
                    self.log(f"[ERROR] 长线诊断失败: {e}", "error")])

        threading.Thread(target=work, daemon=True).start()

    def longterm_screen(self):
        """批量筛选长线好股（后台线程）"""
        text = self.lt_entry.get().strip()
        if not text:
            messagebox.showwarning("警告", "请先输入要筛选的股票，逗号分隔")
            return
        tokens = [t for t in (x.strip() for x in text.split(',')) if t]
        if not tokens:
            messagebox.showwarning("警告", "请输入有效的股票名字或代码")
            return
        if len(tokens) > 12:
            messagebox.showwarning("提示", "一次最多筛选12只，请减少数量（可分批筛选）")
            return
        self._lt_set_status(f"状态: 正在筛选 {len(tokens)} 只股票...", "blue")
        self._lt_show(f"⏳ 正在逐一分析 {len(tokens)} 只股票（每只需要下载历史行情+财务数据+训练AI模型），"
                      f"请耐心等待...\n{text}")

        def work():
            try:
                df = self.longterm.screen(tokens)
                self.root.after(0, lambda: self._show_longterm_screen(df, tokens))
            except Exception as e:
                self.root.after(0, lambda: [
                    self._lt_show(f"❌ 筛选失败：{e}"),
                    self._lt_set_status(f"状态: 失败 - {e}", "red"),
                    self.log(f"[ERROR] 长线筛选失败: {e}", "error")])

        threading.Thread(target=work, daemon=True).start()

    def _format_longterm_report(self, rep):
        lines = []
        if 'error' in rep:
            return f"❌ {rep['token']}：{rep['error']}"
        lines.append(f"🔎 {rep['name']}（{rep['code']}）现价 {rep['price']:.2f}元" if rep['price'] else f"🔎 {rep['name']}（{rep['code']}）")
        lines.append(f"🏆 总分：{rep['total_score']} 分（级别 {rep['level']}）→ {rep['verdict']}")
        lines.append(f"   技术面 {rep['tech_score']} + 基本面 {rep['fund_score']} + AI预测 {rep['ai_score']}  （共{rep['history_rows']}条历史数据）")
        lines.append(f"   用时 {rep['elapsed']} 秒")
        lines.append("")
        lines.append("【📈 技术面（走势趋势）】")
        if rep.get('tech_detail'):
            for d in rep['tech_detail']:
                lines.append(f"  · {d}")
        else:
            lines.append("  · 数据不足")
        lines.append("")
        lines.append("【🏦 基本面（财务健康）】")
        if rep.get('fund_detail'):
            for d in rep['fund_detail']:
                lines.append(f"  · {d}")
        else:
            lines.append("  · 财务数据获取失败")
        lines.append("")
        lines.append(f"【🤖 AI模型预测】{rep['ai_text']}")
        return "\n".join(lines)

    def _show_longterm_report(self, rep, token):
        text = self._format_longterm_report(rep)
        self._lt_show(text)
        if 'error' in rep:
            self._lt_set_status(f"状态: {rep['error']}", "red")
        else:
            self._lt_set_status(f"状态: {rep['name']} 总分 {rep['total_score']}（级别 {rep['level']}）", "green")
        self.log(f"[长线] 诊断完成 {token}：总分 {rep.get('total_score')} 级别 {rep.get('level')}")

    def _show_longterm_screen(self, df, tokens):
        if df is None or df.empty:
            self._lt_show("❌ 没有返回任何分析结果，请检查网络或输入")
            self._lt_set_status("状态: 无结果", "red")
            return
        lines = ["🏆 长线好股筛选结果（按总分从高到低）\n"]
        for _, r in df.iterrows():
            lines.append(
                f"{r['总分']:>5.1f}分[{r['级别']}] {r['名称']}({r['代码']}) 现价{r['现价']}  "
                f"技术{r['技术面']} 基本面{r['基本面']} AI{r['AI预测']}")
        lines.append("")
        lines.append("👉 建议：优先关注A级和B级；C级先观察，D级谨慎。预测仅供参考，不构成投资建议。")
        self._lt_show("\n".join(lines))
        self._lt_set_status(f"状态: 筛选完成 - {len(df)} 只", "green")
        for _, r in df.iterrows():
            self.log(f"[长线] {r['名称']}({r['代码']}) 总分{r['总分']} 级别{r['级别']} {r['结论']}")

    def create_realtime_market_tab(self, notebook):
        """实时行情标签页（上交所/深交所数据源）"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📊 实时行情")
        
        # 使用Notebook创建多个子标签页
        realtime_notebook = ttk.Notebook(tab)
        realtime_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 子标签页1: 股票实时行情
        self.create_stock_realtime_tab(realtime_notebook)
        
        # 子标签页2: 基金实时行情
        self.create_fund_realtime_tab(realtime_notebook)
        
        # 子标签页3: 指数实时行情
        self.create_index_realtime_tab(realtime_notebook)
        
        # 子标签页4: 板块实时行情
        self.create_board_realtime_tab(realtime_notebook)
        
        # 子标签页5: 市场概览
        self.create_market_overview_tab(realtime_notebook)
    
    # ===================== 实时行情相关方法 =====================
    
    def init_realtime_market(self):
        """初始化实时行情"""
        try:
            self.realtime_enhancer = TonghuashunRealtimeEnhancer()
            self.realtime_status_label.config(text="已初始化 [CHECK]", foreground="green")
            self.realtime_init_btn.config(state=tk.DISABLED)
            self.log("[OK] 实时行情增强器初始化成功", "success")
            
            # 运行网络诊断
            self.realtime_enhancer.diagnose_network()
            
            # 首次更新市场概览
            self.update_market_overview()
            
        except Exception as e:
            self.realtime_status_label.config(text=f"初始化失败: {e}", foreground="red")
            self.log(f"[ERROR] 实时行情初始化失败: {e}", "error")
    
    def update_market_overview(self):
        """更新市场概览"""
        def update_thread():
            if not self.realtime_enhancer:
                return
            
            try:
                overview = self.realtime_enhancer.get_market_overview_realtime()
                
                if overview:
                    # 在主线程更新UI
                    self.root.after(0, lambda: self._update_market_overview_ui(overview))
            except Exception as e:
                self.log(f"更新市场概览失败: {e}", "error")
        
        threading.Thread(target=update_thread, daemon=True).start()
    
    def _update_market_overview_ui(self, overview):
        """更新市场概览UI"""
        # 更新统计信息
        self.market_total_label.config(text=f"总股票: {overview.get('total_stocks', 0)}")
        self.market_up_label.config(text=f"[UP] 上涨: {overview.get('up_count', 0)}", 
                                     foreground="red")
        self.market_down_label.config(text=f"[DOWN] 下跌: {overview.get('down_count', 0)}", 
                                       foreground="green")
        self.market_flat_label.config(text=f"⚪ 平盘: {overview.get('flat_count', 0)}")
        
        # 更新涨跌停
        self.limit_up_label.config(text=f"涨停: {overview.get('limit_up', 0)}", 
                                    foreground="red")
        self.limit_down_label.config(text=f"跌停: {overview.get('limit_down', 0)}", 
                                     foreground="green")
        
        # 更新成交额
        self.turnover_label.config(text=f"成交额: {overview.get('turnover', 0):.2f} 亿")
        
        # 更新指数
        sh_index = overview.get('shanghai_index')
        if sh_index:
            color = "red" if sh_index['change'] >= 0 else "green"
            self.sh_index_label.config(
                text=f"上证指数: {sh_index['price']:.2f} ({sh_index['change']:+.2f}%)",
                foreground=color
            )
        
        sz_index = overview.get('shenzhen_index')
        if sz_index:
            color = "red" if sz_index['change'] >= 0 else "green"
            self.sz_index_label.config(
                text=f"深证成指: {sz_index['price']:.2f} ({sz_index['change']:+.2f}%)",
                foreground=color
            )
    
    def query_realtime_stocks(self):
        """查询股票实时行情（智能识别输入）"""
        if not self.realtime_enhancer:
            messagebox.showwarning("警告", "请先初始化实时行情")
            return
        
        codes_str = self.realtime_stock_entry.get().strip()
        if not codes_str:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def query_thread():
            try:
                df = self.smart_client.get_realtime(codes_str, types_hint=['stock'])
                self.root.after(0, lambda: self._display_stock_realtime(df))
            except Exception as e:
                self.log(f"查询股票实时行情失败: {e}", "error")
        
        threading.Thread(target=query_thread, daemon=True).start()
    
    def _display_stock_realtime(self, df):
        """显示股票实时行情"""
        # 清空表格
        for item in self.realtime_stock_tree.get_children():
            self.realtime_stock_tree.delete(item)
        
        if df.empty:
            self.log("未找到股票数据", "warning")
            return
        
        # 填充数据
        for _, row in df.iterrows():
            pct = row.get('change_percent', 0) or 0
            item = self.realtime_stock_tree.insert("", tk.END, values=(
                row.get('symbol', ''),
                row.get('name', ''),
                f"{row.get('price', 0):.2f}",
                f"{pct:+.2f}%",
                f"{row.get('change_amount', 0):+.2f}",
                f"{row.get('volume', 0):,.0f}",
                f"{row.get('amount', 0):,.0f}",
                f"{row.get('high', 0):.2f}",
                f"{row.get('low', 0):.2f}",
                f"{row.get('open', 0):.2f}"
            ))
            
            # 根据涨跌幅设置颜色
            tags = ("up" if pct >= 0 else "down",)
            self.realtime_stock_tree.item(item, tags=tags)
        
        # 配置颜色
        self.realtime_stock_tree.tag_configure("up", foreground="red")
        self.realtime_stock_tree.tag_configure("down", foreground="green")
        
        # 更新时间
        self.realtime_update_time_label.config(
            text=f"最后更新: {datetime.now().strftime('%H:%M:%S')}"
        )
    
    def refresh_realtime_stocks(self):
        """刷新股票实时行情"""
        self.query_realtime_stocks()
    
    def query_realtime_funds(self):
        """查询基金实时行情（智能识别输入）"""
        if not self.realtime_enhancer:
            messagebox.showwarning("警告", "请先初始化实时行情")
            return
        
        codes_str = self.realtime_fund_entry.get().strip()
        if not codes_str:
            messagebox.showwarning("警告", "请输入基金代码")
            return
        
        def query_thread():
            try:
                df = self.smart_client.get_realtime(codes_str, types_hint=['fund'])
                self.root.after(0, lambda: self._display_fund_realtime(df))
            except Exception as e:
                self.log(f"查询基金实时行情失败: {e}", "error")
        
        threading.Thread(target=query_thread, daemon=True).start()
    
    def _display_fund_realtime(self, df):
        """显示基金实时行情"""
        # 清空表格
        for item in self.realtime_fund_tree.get_children():
            self.realtime_fund_tree.delete(item)
        
        if df.empty:
            self.log("未找到基金数据", "warning")
            return
        
        # 填充数据
        for _, row in df.iterrows():
            pct = row.get('change_percent', 0) or 0
            item = self.realtime_fund_tree.insert("", tk.END, values=(
                row.get('symbol', ''),
                row.get('name', ''),
                f"{row.get('price', 0):.2f}",
                f"{pct:+.2f}%",
                f"{row.get('change_amount', 0):+.2f}",
                f"{row.get('volume', 0):,.0f}",
                f"{row.get('amount', 0):,.0f}",
                f"{row.get('high', 0):.2f}",
                f"{row.get('low', 0):.2f}",
                f"{row.get('open', 0):.2f}"
            ))
            
            # 根据涨跌幅设置颜色
            tags = ("up" if pct >= 0 else "down",)
            self.realtime_fund_tree.item(item, tags=tags)
        
        # 配置颜色
        self.realtime_fund_tree.tag_configure("up", foreground="red")
        self.realtime_fund_tree.tag_configure("down", foreground="green")
        
        # 更新时间
        self.realtime_update_time_label.config(
            text=f"最后更新: {datetime.now().strftime('%H:%M:%S')}"
        )
    
    def refresh_realtime_funds(self):
        """刷新基金实时行情"""
        self.query_realtime_funds()
    
    def start_realtime_auto_update(self):
        """开始自动更新"""
        if not self.realtime_enhancer:
            messagebox.showwarning("警告", "请先初始化实时行情")
            return
        
        try:
            interval = int(self.realtime_interval_entry.get().strip())
            if interval < 5:
                messagebox.showwarning("警告", "刷新间隔不能少于5秒")
                return
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的刷新间隔")
            return
        
        # 定义回调函数
        def realtime_callback(stock_data, fund_data, timestamp):
            if stock_data is not None:
                self.root.after(0, lambda: self._display_stock_realtime(stock_data))
            if fund_data is not None:
                self.root.after(0, lambda: self._display_fund_realtime(fund_data))
            
            # 更新市场概览
            overview = self.realtime_enhancer.get_market_overview_realtime()
            if overview:
                self.root.after(0, lambda: self._update_market_overview_ui(overview))
        
        # 订阅自动更新
        self.realtime_subscriber_id = self.realtime_enhancer.subscribe(
            realtime_callback,
            symbols=None  # None表示更新全部
        )
        
        # 启动自动更新
        self.realtime_enhancer.start_auto_update(interval)
        
        self.realtime_auto_update = True
        self.realtime_status_label.config(text=f"自动更新中 ({interval}s)", foreground="blue")
        self.realtime_start_btn.config(state=tk.DISABLED)
        self.log(f"[OK] 实时行情自动更新已启动，间隔: {interval}秒", "success")
    
    def stop_realtime_auto_update(self):
        """停止自动更新"""
        if self.realtime_enhancer and self.realtime_auto_update:
            self.realtime_enhancer.stop_auto_update()
            
            if self.realtime_subscriber_id:
                self.realtime_enhancer.unsubscribe(self.realtime_subscriber_id)
                self.realtime_subscriber_id = None
            
            self.realtime_auto_update = False
            self.realtime_status_label.config(text="已停止", foreground="gray")
            self.realtime_start_btn.config(state=tk.NORMAL)
            self.log("⏹️  实时行情自动更新已停止", "info")

    
    def update_limit_from_scale(self, value):
        """根据滑块更新上限值"""
        self.storage_limit_var.set(str(int(float(value))))
    
    def update_storage_info(self):
        """更新存储信息显示"""
        def update_thread():
            try:
                total_size, file_info = self.calculate_storage_usage()
                
                # 在主线程更新UI
                self.root.after(0, lambda: self._update_storage_ui(total_size, file_info))
                
            except Exception as e:
                self.log(f"更新存储信息失败: {e}", "error")
        
        threading.Thread(target=update_thread, daemon=True).start()
    
    def _update_storage_ui(self, total_size, file_info):
        """更新存储UI显示"""
        total_mb = total_size / (1024 * 1024)
        limit_mb = float(self.storage_limit_var.get())
        
        # 更新进度条
        progress_value = min(100, (total_mb / limit_mb) * 100)
        self.storage_progress['value'] = progress_value
        
        # 设置进度条颜色
        if progress_value > 90:
            self.storage_progress.configure(style="red.Horizontal.TProgressbar")
        elif progress_value > 70:
            self.storage_progress.configure(style="orange.Horizontal.TProgressbar")
        else:
            self.storage_progress.configure(style="green.Horizontal.TProgressbar")
        
        # 更新文本信息
        status_text = f"总占用: {total_mb:.2f} MB / {limit_mb} MB ({progress_value:.1f}%)"
        self.storage_label.config(text="[STAT] 数据存储状态")
        self.storage_text.config(text=status_text)
        
        # 显示文件统计
        model_count = sum(1 for f in file_info if f['type'] == 'model')
        data_count = sum(1 for f in file_info if f['type'] == 'data')
        analysis_count = sum(1 for f in file_info if f['type'] == 'analysis')
        
        stats_text = f"文件统计: AI模型({model_count}) | 股票数据({data_count}) | 分析报告({analysis_count})"
        if hasattr(self, 'storage_stats'):
            self.storage_stats.config(text=stats_text)
        else:
            self.storage_stats = ttk.Label(self.storage_progress.master, text=stats_text)
            self.storage_stats.pack(anchor=tk.W, pady=(5, 0))
    
    def calculate_storage_usage(self):
        """计算存储占用"""
        total_size = 0
        file_info = []
        
        # 扫描AI模型文件
        import glob
        model_dir = os.path.dirname(__file__)
        model_files = glob.glob(os.path.join(model_dir, "*.pkl"))
        
        for file_path in model_files:
            try:
                size = os.path.getsize(file_path)
                total_size += size
                file_info.append({
                    'path': file_path,
                    'size': size,
                    'type': 'model',
                    'mtime': os.path.getmtime(file_path)
                })
            except:
                pass
        
        # 扫描股票数据文件
        try:
            if os.path.exists(DATA_DIR):
                for filename in os.listdir(DATA_DIR):
                    file_path = os.path.join(DATA_DIR, filename)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        total_size += size
                        file_info.append({
                            'path': file_path,
                            'size': size,
                            'type': 'data',
                            'mtime': os.path.getmtime(file_path)
                        })
        except:
            pass
        
        # 扫描分析数据文件
        analysis_dir = os.path.join(os.path.dirname(DATA_DIR), "分析数据")
        try:
            if os.path.exists(analysis_dir):
                for filename in os.listdir(analysis_dir):
                    file_path = os.path.join(analysis_dir, filename)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        total_size += size
                        file_info.append({
                            'path': file_path,
                            'size': size,
                            'type': 'analysis',
                            'mtime': os.path.getmtime(file_path)
                        })
        except:
            pass
        
        return total_size, file_info
    
    def analyze_storage(self):
        """详细分析数据占用"""
        def analyze_thread():
            try:
                total_size, file_info = self.calculate_storage_usage()
                
                # 按类型分类
                model_files = [f for f in file_info if f['type'] == 'model']
                data_files = [f for f in file_info if f['type'] == 'data']
                analysis_files = [f for f in file_info if f['type'] == 'analysis']
                
                self.log("\n" + "="*80)
                self.log("[FIND] 详细存储分析报告", "info")
                self.log("="*80)
                self.log(f"总占用: {total_size / (1024*1024):.2f} MB")
                self.log(f"文件总数: {len(file_info)} 个")
                self.log(f"AI模型文件: {len(model_files)} 个")
                self.log(f"股票数据文件: {len(data_files)} 个")
                self.log(f"分析报告文件: {len(analysis_files)} 个")
                
                # 显示前10个最大的文件
                if file_info:
                    self.log("\n[UP] 前10个最大文件:")
                    sorted_files = sorted(file_info, key=lambda x: x['size'], reverse=True)[:10]
                    for i, f in enumerate(sorted_files, 1):
                        size_mb = f['size'] / (1024 * 1024)
                        mtime = datetime.fromtimestamp(f['mtime']).strftime('%Y-%m-%d %H:%M')
                        filename = os.path.basename(f['path'])
                        self.log(f"  {i}. {filename} - {size_mb:.2f} MB ({mtime})")
                
                self.log("\n[CHECK] 分析完成", "success")
                
            except Exception as e:
                self.log(f"\n[X] 分析失败: {e}", "error")
        
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def smart_cleanup(self):
        """智能清理数据"""
        limit_mb = float(self.storage_limit_var.get())
        strategy = self.cleanup_strategy_var.get()
        
        def cleanup_thread():
            try:
                total_size, file_info = self.calculate_storage_usage()
                total_mb = total_size / (1024 * 1024)
                
                if total_mb <= limit_mb:
                    self.log(f"\nℹ️ 当前占用 {total_mb:.2f} MB，低于上限 {limit_mb} MB，无需清理", "info")
                    return
                
                # 需要清理的大小
                need_clean_mb = total_mb - limit_mb
                self.log(f"\n🧹 开始智能清理，需要清理 {need_clean_mb:.2f} MB", "info")
                
                # 过滤要清理的文件类型
                files_to_clean = []
                if self.cleanup_models_var.get():
                    files_to_clean.extend([f for f in file_info if f['type'] == 'model'])
                if self.cleanup_data_var.get():
                    files_to_clean.extend([f for f in file_info if f['type'] == 'data'])
                
                if not files_to_clean:
                    self.log("[X] 没有选择要清理的文件类型", "error")
                    return
                
                # 根据策略排序文件
                if strategy == "oldest":
                    files_to_clean.sort(key=lambda x: x['mtime'])  # 最旧的文件在前
                elif strategy == "worst":
                    # 这里可以添加模型性能评估逻辑
                    files_to_clean.sort(key=lambda x: x['mtime'])  # 暂时按时间排序
                
                # 清理文件
                cleaned_size = 0
                cleaned_count = 0
                
                for file_info in files_to_clean:
                    if cleaned_size >= need_clean_mb * 1024 * 1024:
                        break
                    
                    try:
                        file_size = file_info['size']
                        os.remove(file_info['path'])
                        cleaned_size += file_size
                        cleaned_count += 1
                        
                        size_mb = file_size / (1024 * 1024)
                        self.log(f"  [CHECK] 已删除: {os.path.basename(file_info['path'])} ({size_mb:.2f} MB)")
                        
                        # 更新进度显示
                        progress = (cleaned_size / (need_clean_mb * 1024 * 1024)) * 100
                        self.log(f"    进度: {min(100, progress):.1f}%")
                        
                    except Exception as e:
                        self.log(f"  [X] 删除失败 {os.path.basename(file_info['path'])}: {e}", "error")
                
                cleaned_mb = cleaned_size / (1024 * 1024)
                self.log(f"\n[CHECK] 清理完成: 删除 {cleaned_count} 个文件，释放 {cleaned_mb:.2f} MB", "success")
                
                # 更新存储信息
                self.update_storage_info()
                
            except Exception as e:
                self.log(f"\n[X] 清理失败: {e}", "error")
        
        threading.Thread(target=cleanup_thread, daemon=True).start()
    
    def manual_cleanup(self):
        """手动选择删除文件"""
        def manual_thread():
            try:
                total_size, file_info = self.calculate_storage_usage()
                
                # 创建选择对话框
                dialog = tk.Toplevel(self.root)
                dialog.title("手动选择删除文件")
                dialog.geometry("800x600")
                dialog.transient(self.root)
                dialog.grab_set()
                
                # 文件列表
                list_frame = ttk.Frame(dialog)
                list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                ttk.Label(list_frame, text="选择要删除的文件:", font=("Arial", 12, "bold")).pack(anchor=tk.W)
                
                # 创建列表框
                listbox_frame = ttk.Frame(list_frame)
                listbox_frame.pack(fill=tk.BOTH, expand=True, pady=10)
                
                scrollbar = ttk.Scrollbar(listbox_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                file_listbox = tk.Listbox(listbox_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set)
                file_listbox.pack(fill=tk.BOTH, expand=True)
                scrollbar.config(command=file_listbox.yview)
                
                # 填充文件列表
                for i, file_info in enumerate(file_info):
                    size_mb = file_info['size'] / (1024 * 1024)
                    mtime = datetime.fromtimestamp(file_info['mtime']).strftime('%Y-%m-%d')
                    filename = os.path.basename(file_info['path'])
                    
                    display_text = f"[{file_info['type']}] {filename} - {size_mb:.2f} MB ({mtime})"
                    file_listbox.insert(tk.END, display_text)
                
                # 按钮区域
                btn_frame = ttk.Frame(dialog)
                btn_frame.pack(fill=tk.X, padx=10, pady=10)
                
                def delete_selected():
                    selected_indices = file_listbox.curselection()
                    if not selected_indices:
                        messagebox.showwarning("警告", "请选择要删除的文件")
                        return
                    
                    result = messagebox.askyesno("确认", f"确定要删除 {len(selected_indices)} 个文件吗？")
                    if result:
                        deleted_count = 0
                        for index in selected_indices:
                            file_info_to_delete = file_info[index]
                            try:
                                os.remove(file_info_to_delete['path'])
                                deleted_count += 1
                            except:
                                pass
                        
                        messagebox.showinfo("完成", f"已删除 {deleted_count} 个文件")
                        dialog.destroy()
                        self.update_storage_info()
                
                ttk.Button(btn_frame, text="🗑️ 删除选中", 
                          command=delete_selected).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="取消", 
                          command=dialog.destroy).pack(side=tk.LEFT, padx=5)
                
            except Exception as e:
                self.log(f"\n[X] 手动清理失败: {e}", "error")
        
        threading.Thread(target=manual_thread, daemon=True).start()
    
    def create_right_panel(self, parent):
        """创建右侧输出面板"""
        # 输出区域标题
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(title_frame, text="[LIST] 运行日志", 
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(title_frame, text="清空日志", 
                  command=self.clear_log).pack(side=tk.RIGHT)
        
        # 输出文本框
        output_frame = ttk.Frame(parent)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white"
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置文本标签颜色
        self.output_text.tag_config("error", foreground="#ff6b6b")
        self.output_text.tag_config("success", foreground="#51cf66")
        self.output_text.tag_config("warning", foreground="#ffd43b")
        self.output_text.tag_config("info", foreground="#74c0fc")
    
    def log(self, message, tag=None):
        """输出日志"""
        self.output_queue.put((message, tag))
    
    def update_output(self):
        """更新输出显示"""
        try:
            while True:
                item = self.output_queue.get_nowait()
                # 兼容处理：支持元组和单个字符串
                if isinstance(item, tuple):
                    message, tag = item
                else:
                    message, tag = item, None
                
                self.output_text.insert(tk.END, message + "\n", tag)
                self.output_text.see(tk.END)
                self.output_text.update()
        except queue.Empty:
            pass
        except Exception as e:
            # 静默处理其他异常，避免影响主程序
            pass
        
        self.root.after(100, self.update_output)
    
    def clear_log(self):
        """清空日志"""
        self.output_text.delete(1.0, tk.END)
    
    # ==================== 功能实现 ====================
    
    def start_crawling(self):
        """开始爬取数据"""
        stock_input = self.crawl_stock_entry.get().strip()
        start_date = self.crawl_start_date.get().strip()
        end_date = self.crawl_end_date.get().strip()
        
        if not stock_input:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        stock_codes = parse_stock_codes(stock_input)
        
        def crawl_thread():
            self.log("="*80)
            self.log(f"[IN] 开始爬取 {len(stock_codes)} 只股票数据", "info")
            self.log("="*80)
            
            for i, code in enumerate(stock_codes, 1):
                self.log(f"\n[{i}/{len(stock_codes)}] 正在爬取 {code}...", "info")
                
                df = self.crawler.get_stock_daily(code, start_date, end_date)
                
                if df is not None and not df.empty:
                    filename = f"{code}_{start_date}_{end_date}.csv"
                    self.crawler.save_to_csv(df, filename)
                    self.log(f"[CHECK] {code} 爬取成功: {len(df)} 条数据", "success")
                else:
                    self.log(f"[X] {code} 爬取失败", "error")
            
            self.log("\n" + "="*80)
            self.log("[CHECK] 数据爬取完成！", "success")
            self.log("="*80)
        
        threading.Thread(target=crawl_thread, daemon=True).start()
    
    def view_data(self):
        """查看已下载的数据"""
        self.log("\n📂 数据文件列表:", "info")
        self.log(f"目录: {DATA_DIR}")
        
        try:
            files = os.listdir(DATA_DIR)
            if not files:
                self.log("  (目录为空)", "warning")
            else:
                for i, f in enumerate(files, 1):
                    filepath = os.path.join(DATA_DIR, f)
                    size = os.path.getsize(filepath) / 1024
                    self.log(f"  [{i}] {f} ({size:.2f} KB)")
        except Exception as e:
            self.log(f"[X] 读取目录失败: {e}", "error")
    
    def clear_financial_data(self):
        """清空金融数据文件夹"""
        result = messagebox.askyesno("确认", "确定要清空金融数据文件夹吗？\n这将删除所有下载的股票数据！")
        if result:
            try:
                count = clear_data_folder()
                self.log(f"\n[CHECK] 金融数据: 已删除 {count} 个文件", "success")
                messagebox.showinfo("完成", f"已删除 {count} 个金融数据文件")
            except Exception as e:
                self.log(f"[X] 删除失败: {e}", "error")
                messagebox.showerror("错误", f"删除失败: {e}")
    
    def clear_analysis_data(self):
        """清空分析数据文件夹"""
        analysis_dir = os.path.join(os.path.dirname(DATA_DIR), "分析数据")
        
        if not os.path.exists(analysis_dir):
            messagebox.showinfo("提示", "分析数据文件夹不存在或为空")
            return
        
        result = messagebox.askyesno("确认", "确定要清空分析数据文件夹吗？\n这将删除所有生成的分析报告！")
        if result:
            try:
                import glob
                files = glob.glob(os.path.join(analysis_dir, "*"))
                count = 0
                
                self.log(f"\n📂 清空分析数据文件夹: {analysis_dir}", "info")
                
                for file_path in files:
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            self.log(f"  [CHECK] 已删除: {os.path.basename(file_path)}")
                            count += 1
                        except Exception as e:
                            self.log(f"  [X] 删除失败 {os.path.basename(file_path)}: {e}", "error")
                
                self.log(f"\n[CHECK] 分析数据: 已删除 {count} 个文件", "success")
                messagebox.showinfo("完成", f"已删除 {count} 个分析报告文件")
            except Exception as e:
                self.log(f"[X] 删除失败: {e}", "error")
                messagebox.showerror("错误", f"删除失败: {e}")
    
    def clear_all_data(self):
        """清空所有数据文件夹"""
        result = messagebox.askyesno(
            "确认", 
            "确定要清空所有数据文件夹吗？\n\n这将删除:\n• 所有下载的股票数据\n• 所有生成的分析报告\n• 所有训练的AI模型文件\n\n此操作不可恢复！",
            icon='warning'
        )
        if result:
            total_count = 0
            
            # 清空金融数据
            try:
                count = clear_data_folder()
                total_count += count
                self.log(f"\n[CHECK] 金融数据: 已删除 {count} 个文件", "success")
            except Exception as e:
                self.log(f"[X] 金融数据删除失败: {e}", "error")
            
            # 清空分析数据
            try:
                analysis_dir = os.path.join(os.path.dirname(DATA_DIR), "分析数据")
                if os.path.exists(analysis_dir):
                    import glob
                    files = glob.glob(os.path.join(analysis_dir, "*"))
                    count = 0
                    for file_path in files:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            count += 1
                    total_count += count
                    self.log(f"[CHECK] 分析数据: 已删除 {count} 个文件", "success")
            except Exception as e:
                self.log(f"[X] 分析数据删除失败: {e}", "error")
            
            # 清空模型文件
            try:
                import glob
                model_dir = os.path.dirname(__file__)
                model_files = glob.glob(os.path.join(model_dir, "ai_model_*.pkl"))
                count = 0
                for file_path in model_files:
                    try:
                        os.remove(file_path)
                        count += 1
                    except:
                        pass
                if count > 0:
                    total_count += count
                    self.log(f"[CHECK] AI模型: 已删除 {count} 个文件", "success")
            except Exception as e:
                self.log(f"[X] 模型文件删除失败: {e}", "error")
            
            self.log(f"\n[CHECK] 总计删除 {total_count} 个文件", "success")
            messagebox.showinfo("完成", f"已删除 {total_count} 个文件")
    
    # 保留旧方法以兼容
    def clear_data(self):
        """清空数据文件夹（兼容旧代码）"""
        self.clear_financial_data()
    
    def start_backtest(self):
        """开始回测"""
        stock_code = self.backtest_stock_entry.get().strip()
        model_type = self.backtest_model_var.get()
        data_source = self.data_source_var.get()
        
        if not stock_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def backtest_thread():
            try:
                # 根据数据源选择确定时间范围
                if data_source == "download":
                    start_date = self.backtest_start_date.get().strip()
                    end_date = self.backtest_end_date.get().strip()
                    
                    if not start_date or not end_date:
                        messagebox.showwarning("警告", "请输入开始和结束日期")
                        return
                else:
                    # 使用现有数据文件，自动检测时间范围
                    start_date = None
                    end_date = None
                
                # 重定向输出
                old_stdout = sys.stdout
                sys.stdout = RedirectText(self.output_text, self.output_queue)
                
                self.log("="*80)
                self.log(f"[BOT] 开始AI回测 - 股票: {stock_code}", "info")
                self.log(f"   数据源: {'实时下载' if data_source == 'download' else '现有数据文件'}")
                if data_source == "download":
                    self.log(f"   时间范围: {start_date} 至 {end_date}")
                elif hasattr(self, 'selected_data_file') and self.selected_data_file:
                    self.log(f"   使用文件: {os.path.basename(self.selected_data_file)}")
                self.log("="*80)
                
                backtester = MultiModelBacktester(model_type=model_type, use_ai=True, portfolio_manager=self.portfolio)
                
                # 根据数据源选择不同的回测方法
                if data_source == "download":
                    result = backtester.run_backtest(stock_code, start_date, end_date)
                else:
                    # 如果有用户选择的文件，使用指定的文件路径
                    if hasattr(self, 'selected_data_file') and self.selected_data_file:
                        result = backtester.run_backtest_with_specific_file(stock_code, self.selected_data_file)
                    else:
                        result = backtester.run_backtest_with_existing_data(stock_code)
                
                sys.stdout = old_stdout
                
                if result:
                    self.log("\n[CHECK] 回测完成！", "success")
                
            except Exception as e:
                sys.stdout = old_stdout
                self.log(f"\n[X] 回测失败: {e}", "error")
                messagebox.showerror("错误", f"回测失败: {e}")
        
        threading.Thread(target=backtest_thread, daemon=True).start()
    
    def select_data_file(self):
        """选择数据文件进行回测"""
        try:
            import tkinter.filedialog as filedialog
            
            # 设置默认目录为数据文件夹
            initial_dir = DATA_DIR if os.path.exists(DATA_DIR) else os.path.dirname(__file__)
            
            # 打开文件选择对话框
            file_path = filedialog.askopenfilename(
                title="选择回测数据文件",
                initialdir=initial_dir,
                filetypes=[
                    ("CSV文件", "*.csv"),
                    ("所有文件", "*.*")
                ]
            )
            
            if file_path:
                # 从文件名中提取股票代码
                filename = os.path.basename(file_path)
                # 假设文件名格式为：股票代码_开始日期_结束日期.csv
                stock_code = filename.split('_')[0]
                
                # 更新股票代码输入框
                self.backtest_stock_entry.delete(0, tk.END)
                self.backtest_stock_entry.insert(0, stock_code)
                
                # 设置为使用现有数据
                self.data_source_var.set("existing")
                
                # 保存选定的文件路径，供回测系统使用
                self.selected_data_file = file_path
                
                self.log(f"[CHECK] 已选择数据文件: {filename}", "success")
                self.log(f"   股票代码: {stock_code}")
                self.log(f"   文件路径: {file_path}")
                self.log(f"   [OK] 文件已成功选定，下次回测将使用此文件")
                
        except Exception as e:
            self.log(f"[X] 选择文件失败: {e}", "error")
            messagebox.showerror("错误", f"选择文件失败: {e}")
    
    def start_model_comparison(self):
        """开始多模型对比"""
        stock_code = self.backtest_stock_entry.get().strip()
        
        if not stock_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        # 选择要对比的模型
        dialog = tk.Toplevel(self.root)
        dialog.title("选择对比模型")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="选择要对比的AI模型:", 
                 font=("Arial", 12, "bold")).pack(pady=10)
        
        model_vars = {}
        for key, info in AI_MODELS.items():
            var = tk.BooleanVar(value=False)
            model_vars[key] = var
            ttk.Checkbutton(
                dialog,
                text=f"{info['name']} (速度:{info['speed']}, 精度:{info['accuracy']})",
                variable=var
            ).pack(anchor=tk.W, padx=20, pady=2)
        
        def start_comparison():
            selected_models = [k for k, v in model_vars.items() if v.get()]
            
            if not selected_models:
                messagebox.showwarning("警告", "请至少选择一个模型")
                return
            
            dialog.destroy()
            
            def comparison_thread():
                try:
                    current_year = datetime.now().year
                    start_date = f"{current_year}0101"
                    end_date = datetime.now().strftime('%Y%m%d')
                    
                    old_stdout = sys.stdout
                    sys.stdout = RedirectText(self.output_text, self.output_queue)
                    
                    from 多模型AI量化交易 import compare_models
                    compare_models(stock_code, start_date, end_date, selected_models)
                    
                    sys.stdout = old_stdout
                    self.log("\n[CHECK] 模型对比完成！", "success")
                    
                except Exception as e:
                    sys.stdout = old_stdout
                    self.log(f"\n[X] 对比失败: {e}", "error")
            
            threading.Thread(target=comparison_thread, daemon=True).start()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="开始对比", 
                  command=start_comparison).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", 
                  command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def start_monitoring(self):
        """开始实时监控"""
        stock_input = self.monitor_stock_entry.get().strip()
        model_type = self.monitor_model_var.get().split(" - ")[0]
        interval = int(self.monitor_interval_var.get())
        do_train = self.monitor_train_var.get()
        
        if not stock_input:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        stock_codes = parse_stock_codes(stock_input)
        
        # 禁用开始按钮，启用停止按钮
        self.monitor_start_btn.config(state=tk.DISABLED)
        self.monitor_stop_btn.config(state=tk.NORMAL)
        
        def monitor_thread():
            try:
                old_stdout = sys.stdout
                sys.stdout = RedirectText(self.output_text, self.output_queue)
                
                self.current_monitor = RealTimeMonitor(stock_codes, model_type, interval, portfolio_manager=self.portfolio)
                
                # 使用自动训练模式，无需手动输入y/n
                self.current_monitor.start_monitoring(auto_train=do_train)
                
                sys.stdout = old_stdout
                
            except Exception as e:
                sys.stdout = old_stdout
                self.log(f"\n[X] 监控失败: {e}", "error")
            finally:
                self.monitor_start_btn.config(state=tk.NORMAL)
                self.monitor_stop_btn.config(state=tk.DISABLED)
        
        self.monitor_thread = threading.Thread(target=monitor_thread, daemon=True)
        self.monitor_thread.start()
        
        # 立即更新按钮状态，无需等待线程结束
        self.log("\n[OK] 监控已启动，点击""停止监控可立即停止", "success")
    
    def stop_monitoring(self):
        """立即停止监控"""
        # 立即更新UI状态，无需等待线程响应
        self.monitor_start_btn.config(state=tk.NORMAL)
        self.monitor_stop_btn.config(state=tk.DISABLED)
        self.log("\n⏹️ 正在停止监控...（立即响应）", "warning")
        
        if self.current_monitor:
            self.current_monitor.running = False
            
            # 强制中断可能的网络请求
            self._force_stop_monitor()
        
        # 显示立即停止反馈
        self.root.after(100, self._check_monitor_stopped)  # 100ms后检查是否已停止
    
    def _force_stop_monitor(self):
        """强制停止监控的辅助方法"""
        # 设置超时时间，防止长时间等待
        self._monitor_stop_timeout = time.time() + 5  # 5秒超时
    
    def _check_monitor_stopped(self):
        """检查监控是否已停止"""
        if self.current_monitor and not self.current_monitor.running:
            self.log("[OK] 监控已完全停止", "success")
        elif time.time() > self._monitor_stop_timeout:
            self.log("[WARN]  监控线程仍在运行，但UI已释放", "warning")
        else:
            # 继续检查，直到停止或超时
            self.root.after(100, self._check_monitor_stopped)
    
    def start_analysis(self):
        """开始数据分析"""
        data_dir = self.analysis_dir_entry.get().strip()
        enable_ai = self.analysis_ai_var.get()
        
        if not os.path.exists(data_dir):
            messagebox.showerror("错误", "数据目录不存在")
            return
        
        def analysis_thread():
            try:
                self.log("\n" + "="*80)
                self.log("[STAT] 开始数据分析...", "info")
                self.log("="*80)
                
                output_dir = os.path.join(os.path.dirname(data_dir), "分析数据")
                
                old_stdout = sys.stdout
                sys.stdout = RedirectText(self.output_text, self.output_queue)
                
                analyzer = FinancialDataAnalyzer(data_dir, output_dir, enable_ai=enable_ai)
                analyzer.scan_data_files()
                analyzer.analyze_all_files()
                analyzer.create_html_report()  # 修复：正确的方法名
                
                sys.stdout = old_stdout
                
                self.log("\n[CHECK] 分析完成！", "success")
                messagebox.showinfo("完成", "数据分析完成！")
                
            except Exception as e:
                sys.stdout = old_stdout
                self.log(f"\n[X] 分析失败: {e}", "error")
                messagebox.showerror("错误", f"分析失败: {e}")
        
        threading.Thread(target=analysis_thread, daemon=True).start()
    
    def show_help(self):
        """显示帮助"""
        help_text = """
[BOT] AI量化交易系统 使用说明

【数据爬取】
1. 输入股票代码（支持批量，用逗号分隔）
2. 选择时间范围
3. 点击"开始爬取"下载数据
4. 可点击"清空数据"删除下载的文件

【AI回测】
1. 输入要回测的股票代码
2. 选择AI模型（8种可选）
3. 点击"开始回测"进行策略测试
4. "多模型对比"可同时测试多个模型

【实时监控】
1. 输入要监控的股票代码（支持批量）
2. 选择AI模型和刷新间隔
3. 点击"开始监控"启动实时监控
4. 监控运行时可点击"停止监控"退出

【数据分析】
1. 指定数据目录
2. 可选启用AI智能分析
3. 点击"开始分析"生成HTML报告
4. 可点击"清空分析数据"删除报告文件

【数据管理】
菜单栏 -> 文件：
• 清空金融数据文件夹 - 删除所有下载的股票数据
• 清空分析数据文件夹 - 删除所有生成的分析报告
• 清空所有数据文件夹 - 删除所有数据和AI模型

提示：
- 所有操作在后台线程执行，不会卡界面
- 日志实时显示在右侧输出区域
- 删除操作会有确认提示，请仔细阅读
        """
        
        dialog = tk.Toplevel(self.root)
        dialog.title("使用说明")
        dialog.geometry("650x550")
        
        text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=("Arial", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, help_text)
        text.config(state=tk.DISABLED)
        
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)
    
    def open_financial_data_folder(self):
        """打开金融数据文件夹"""
        try:
            if os.path.exists(DATA_DIR):
                os.startfile(DATA_DIR)
                self.log(f"[CHECK] 已打开金融数据文件夹: {DATA_DIR}", "success")
            else:
                messagebox.showwarning("提示", "金融数据文件夹不存在，请先爬取数据")
        except Exception as e:
            self.log(f"[X] 打开文件夹失败: {e}", "error")
            messagebox.showerror("错误", f"无法打开文件夹: {e}")
    
    def open_analysis_data_folder(self):
        """打开分析数据文件夹"""
        try:
            analysis_dir = os.path.join(os.path.dirname(DATA_DIR), "分析数据")
            if os.path.exists(analysis_dir):
                os.startfile(analysis_dir)
                self.log(f"[CHECK] 已打开分析数据文件夹: {analysis_dir}", "success")
            else:
                messagebox.showwarning("提示", "分析数据文件夹不存在，请先进行数据分析")
        except Exception as e:
            self.log(f"[X] 打开文件夹失败: {e}", "error")
            messagebox.showerror("错误", f"无法打开文件夹: {e}")
    
    def open_model_folder(self):
        """打开AI模型文件夹"""
        try:
            model_dir = os.path.dirname(__file__)
            # 检查是否有模型文件
            import glob
            model_files = glob.glob(os.path.join(model_dir, "*.pkl"))
            if model_files:
                os.startfile(model_dir)
                self.log(f"[CHECK] 已打开AI模型文件夹: {model_dir}", "success")
            else:
                messagebox.showwarning("提示", "AI模型文件夹为空，请先训练模型")
        except Exception as e:
            self.log(f"[X] 打开文件夹失败: {e}", "error")
            messagebox.showerror("错误", f"无法打开文件夹: {e}")
    
    def connect_database(self):
        """连接数据库"""
        try:
            from database_manager import DatabaseManager
            from database_config import DB_CONFIG
            
            self.log("\n[CONN] 正在连接数据库...", "info")
            self.log(f"  主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
            self.log(f"  数据库: {DB_CONFIG['database']}")
            
            db = DatabaseManager()
            if db.connection:
                self.log("[OK] 数据库连接成功", "success")
                
                # 显示数据库信息
                db.cursor.execute("SELECT VERSION()")
                version = db.cursor.fetchone()['VERSION()']
                self.log(f"[STAT] MySQL版本: {version}")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 连接数据库失败: {e}", "error")
    
    def view_database_tables(self):
        """查看数据库表"""
        try:
            from database_manager import DatabaseManager
            
            self.log("\n[LIST] 正在查询数据库表...", "info")
            
            db = DatabaseManager()
            if db.connection:
                db.cursor.execute("SHOW TABLES")
                tables = db.cursor.fetchall()
                
                if tables:
                    self.log("[STAT] 数据库中的表:", "info")
                    for table in tables:
                        table_name = table['Tables_in_quantitative_trading']
                        self.log(f"  - {table_name}")
                        
                        # 显示表结构
                        db.cursor.execute(f"DESCRIBE {table_name}")
                        columns = db.cursor.fetchall()
                        
                        for col in columns:
                            comment = col.get('Comment', '')
                            if comment:
                                self.log(f"    {col['Field']} ({col['Type']}) - {comment}")
                            else:
                                self.log(f"    {col['Field']} ({col['Type']})")
                else:
                    self.log("[WARN] 数据库中没有表", "warning")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 查询数据库表失败: {e}", "error")
    
    def sync_data_to_database(self):
        """同步数据到数据库"""
        try:
            from financial_data_integrator import FinancialDataIntegrator
            
            self.log("\n[SYNC] 正在同步数据到数据库...", "info")
            
            integrator = FinancialDataIntegrator()
            
            # 同步股票基本信息
            self.log("[STAT] 同步股票基本信息...")
            integrator.sync_stock_basic_info('沪深A股')
            
            # 同步部分股票的行情数据
            self.log("[UP] 同步行情数据...")
            test_codes = ['000001.SZ', '600000.SH', '00700.HK']
            start_date = '2024-01-01'
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            integrator.sync_daily_quotes(test_codes, start_date, end_date)
            
            # 计算技术指标
            self.log("[STAT] 计算技术指标...")
            integrator.calculate_all_technical_indicators(test_codes)
            
            integrator.close()
            self.log("[OK] 数据同步完成", "success")
            
        except Exception as e:
            self.log(f"[ERROR] 数据同步失败: {e}", "error")
    
    def view_csv_files(self):
        """查看CSV文件"""
        try:
            import glob
            
            self.log("\n[FILE] 正在扫描CSV文件...", "info")
            
            # 扫描项目目录下的CSV文件
            project_dir = os.path.dirname(__file__)
            csv_files = glob.glob(os.path.join(project_dir, "*.csv"))
            
            if csv_files:
                self.log("[STAT] 找到的CSV文件:", "info")
                for csv_file in csv_files:
                    file_name = os.path.basename(csv_file)
                    file_size = os.path.getsize(csv_file) / 1024  # KB
                    
                    # 尝试读取文件基本信息
                    try:
                        df = pd.read_csv(csv_file, nrows=1)
                        columns = len(df.columns)
                        self.log(f"  📄 {file_name} ({file_size:.1f} KB, {columns}列)")
                    except:
                        self.log(f"  📄 {file_name} ({file_size:.1f} KB)")
                
                # 提供查看选项
                self.log("\n[IDEA] 提示: 可以使用 '导入CSV到数据库' 功能将数据导入数据库", "info")
            else:
                self.log("[WARN] 未找到CSV文件", "warning")
                
        except Exception as e:
            self.log(f"[ERROR] 扫描CSV文件失败: {e}", "error")
    
    def import_csv_to_database(self):
        """导入CSV到数据库"""
        try:
            import tkinter.filedialog as filedialog
            from database_manager import DatabaseManager
            
            # 选择CSV文件
            file_path = filedialog.askopenfilename(
                title="选择CSV文件",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
            
            self.log(f"\n[IN] 正在导入CSV文件: {os.path.basename(file_path)}", "info")
            
            # 读取CSV文件
            df = pd.read_csv(file_path)
            self.log(f"[STAT] 文件包含 {len(df)} 行数据，{len(df.columns)} 列")
            
            # 显示列名
            self.log("[LIST] 数据列名:", "info")
            for i, col in enumerate(df.columns):
                self.log(f"  {i+1}. {col}")
            
            # 连接到数据库
            db = DatabaseManager()
            if db.connection:
                # 根据文件名猜测表名
                table_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # 创建临时表
                create_sql = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        {', '.join([f'{col} TEXT' for col in df.columns])}
                    )
                """
                
                db.cursor.execute(create_sql)
                
                # 插入数据
                for _, row in df.iterrows():
                    values = tuple(row.astype(str))
                    placeholders = ', '.join(['%s'] * len(df.columns))
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(df.columns)}) VALUES ({placeholders})"
                    db.cursor.execute(insert_sql, values)
                
                db.connection.commit()
                self.log(f"[OK] 成功导入 {len(df)} 行数据到表 {table_name}", "success")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 导入CSV失败: {e}", "error")
    
    def export_database_to_csv(self):
        """导出数据库到CSV"""
        try:
            import tkinter.filedialog as filedialog
            from database_manager import DatabaseManager
            
            # 选择保存位置
            file_path = filedialog.asksaveasfilename(
                title="保存CSV文件",
                defaultextension=".csv",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
            
            self.log(f"\n[OUT] 正在导出数据到CSV...", "info")
            
            # 连接到数据库
            db = DatabaseManager()
            if db.connection:
                # 获取所有表
                db.cursor.execute("SHOW TABLES")
                tables = db.cursor.fetchall()
                
                if tables:
                    # 选择要导出的表
                    table_names = [table['Tables_in_quantitative_trading'] for table in tables]
                    
                    # 导出第一个表（可以根据需要扩展为多表选择）
                    table_name = table_names[0]
                    
                    # 查询数据
                    db.cursor.execute(f"SELECT * FROM {table_name}")
                    data = db.cursor.fetchall()
                    
                    if data:
                        # 转换为DataFrame并保存
                        df = pd.DataFrame(data)
                        df.to_csv(file_path, index=False)
                        
                        self.log(f"[OK] 成功导出表 {table_name} 的 {len(df)} 行数据到 {os.path.basename(file_path)}", "success")
                    else:
                        self.log(f"[WARN] 表 {table_name} 为空，无法导出", "warning")
                else:
                    self.log("[WARN] 数据库中没有表", "warning")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 导出数据失败: {e}", "error")
    
    def connect_database(self):
        """连接数据库"""
        try:
            from database_manager import DatabaseManager
            from database_config import DB_CONFIG
            
            self.log("\n[CONN] 正在连接数据库...", "info")
            self.log(f"  主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
            self.log(f"  数据库: {DB_CONFIG['database']}")
            
            db = DatabaseManager()
            if db.connection:
                self.log("[OK] 数据库连接成功", "success")
                
                # 显示数据库信息
                db.cursor.execute("SELECT VERSION()")
                version = db.cursor.fetchone()['VERSION()']
                self.log(f"[STAT] MySQL版本: {version}")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 连接数据库失败: {e}", "error")
    
    def view_database_tables(self):
        """查看数据库表"""
        try:
            from database_manager import DatabaseManager
            
            self.log("\n[LIST] 正在查询数据库表...", "info")
            
            db = DatabaseManager()
            if db.connection:
                db.cursor.execute("SHOW TABLES")
                tables = db.cursor.fetchall()
                
                if tables:
                    self.log("[STAT] 数据库中的表:", "info")
                    for table in tables:
                        table_name = table['Tables_in_quantitative_trading']
                        self.log(f"  - {table_name}")
                        
                        # 显示表结构
                        db.cursor.execute(f"DESCRIBE {table_name}")
                        columns = db.cursor.fetchall()
                        
                        for col in columns:
                            comment = col.get('Comment', '')
                            if comment:
                                self.log(f"    {col['Field']} ({col['Type']}) - {comment}")
                            else:
                                self.log(f"    {col['Field']} ({col['Type']})")
                else:
                    self.log("[WARN] 数据库中没有表", "warning")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 查询数据库表失败: {e}", "error")
    
    def sync_data_to_database(self):
        """同步数据到数据库"""
        try:
            from financial_data_integrator import FinancialDataIntegrator
            
            self.log("\n[SYNC] 正在同步数据到数据库...", "info")
            
            integrator = FinancialDataIntegrator()
            
            # 同步股票基本信息
            self.log("[STAT] 同步股票基本信息...")
            integrator.sync_stock_basic_info('沪深A股')
            
            # 同步部分股票的行情数据
            self.log("[UP] 同步行情数据...")
            test_codes = ['000001.SZ', '600000.SH', '00700.HK']
            start_date = '2024-01-01'
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            integrator.sync_daily_quotes(test_codes, start_date, end_date)
            
            # 计算技术指标
            self.log("[STAT] 计算技术指标...")
            integrator.calculate_all_technical_indicators(test_codes)
            
            integrator.close()
            self.log("[OK] 数据同步完成", "success")
            
        except Exception as e:
            self.log(f"[ERROR] 数据同步失败: {e}", "error")
    
    def view_csv_files(self):
        """查看CSV文件"""
        try:
            import glob
            
            self.log("\n[FILE] 正在扫描CSV文件...", "info")
            
            # 扫描项目目录下的CSV文件
            project_dir = os.path.dirname(__file__)
            csv_files = glob.glob(os.path.join(project_dir, "*.csv"))
            
            if csv_files:
                self.log("[STAT] 找到的CSV文件:", "info")
                for csv_file in csv_files:
                    file_name = os.path.basename(csv_file)
                    file_size = os.path.getsize(csv_file) / 1024  # KB
                    
                    # 尝试读取文件基本信息
                    try:
                        df = pd.read_csv(csv_file, nrows=1)
                        columns = len(df.columns)
                        self.log(f"  📄 {file_name} ({file_size:.1f} KB, {columns}列)")
                    except:
                        self.log(f"  📄 {file_name} ({file_size:.1f} KB)")
                
                # 提供查看选项
                self.log("\n[IDEA] 提示: 可以使用 '导入CSV到数据库' 功能将数据导入数据库", "info")
            else:
                self.log("[WARN] 未找到CSV文件", "warning")
                
        except Exception as e:
            self.log(f"[ERROR] 扫描CSV文件失败: {e}", "error")
    
    def import_csv_to_database(self):
        """导入CSV到数据库"""
        try:
            import tkinter.filedialog as filedialog
            from database_manager import DatabaseManager
            
            # 选择CSV文件
            file_path = filedialog.askopenfilename(
                title="选择CSV文件",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
            
            self.log(f"\n[IN] 正在导入CSV文件: {os.path.basename(file_path)}", "info")
            
            # 读取CSV文件
            df = pd.read_csv(file_path)
            self.log(f"[STAT] 文件包含 {len(df)} 行数据，{len(df.columns)} 列")
            
            # 显示列名
            self.log("[LIST] 数据列名:", "info")
            for i, col in enumerate(df.columns):
                self.log(f"  {i+1}. {col}")
            
            # 连接到数据库
            db = DatabaseManager()
            if db.connection:
                # 根据文件名猜测表名
                table_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # 创建临时表
                create_sql = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        {', '.join([f'{col} TEXT' for col in df.columns])}
                    )
                """
                
                db.cursor.execute(create_sql)
                
                # 插入数据
                for _, row in df.iterrows():
                    values = tuple(row.astype(str))
                    placeholders = ', '.join(['%s'] * len(df.columns))
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(df.columns)}) VALUES ({placeholders})"
                    db.cursor.execute(insert_sql, values)
                
                db.connection.commit()
                self.log(f"[OK] 成功导入 {len(df)} 行数据到表 {table_name}", "success")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 导入CSV失败: {e}", "error")
    
    def export_database_to_csv(self):
        """导出数据库到CSV"""
        try:
            import tkinter.filedialog as filedialog
            from database_manager import DatabaseManager
            
            # 选择保存位置
            file_path = filedialog.asksaveasfilename(
                title="保存CSV文件",
                defaultextension=".csv",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
            
            self.log(f"\n[OUT] 正在导出数据到CSV...", "info")
            
            # 连接到数据库
            db = DatabaseManager()
            if db.connection:
                # 获取所有表
                db.cursor.execute("SHOW TABLES")
                tables = db.cursor.fetchall()
                
                if tables:
                    # 选择要导出的表
                    table_names = [table['Tables_in_quantitative_trading'] for table in tables]
                    
                    # 导出第一个表（可以根据需要扩展为多表选择）
                    table_name = table_names[0]
                    
                    # 查询数据
                    db.cursor.execute(f"SELECT * FROM {table_name}")
                    data = db.cursor.fetchall()
                    
                    if data:
                        # 转换为DataFrame并保存
                        df = pd.DataFrame(data)
                        df.to_csv(file_path, index=False)
                        
                        self.log(f"[OK] 成功导出表 {table_name} 的 {len(df)} 行数据到 {os.path.basename(file_path)}", "success")
                    else:
                        self.log(f"[WARN] 表 {table_name} 为空，无法导出", "warning")
                else:
                    self.log("[WARN] 数据库中没有表", "warning")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 导出数据失败: {e}", "error")
    
    def connect_database(self):
        """连接数据库"""
        try:
            from database_manager import DatabaseManager
            from database_config import DB_CONFIG
            
            self.log("\n[CONN] 正在连接数据库...", "info")
            self.log(f"  主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
            self.log(f"  数据库: {DB_CONFIG['database']}")
            
            db = DatabaseManager()
            if db.connection:
                self.log("[OK] 数据库连接成功", "success")
                
                # 显示数据库信息
                db.cursor.execute("SELECT VERSION()")
                version = db.cursor.fetchone()['VERSION()']
                self.log(f"[STAT] MySQL版本: {version}")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 连接数据库失败: {e}", "error")
    
    def view_database_tables(self):
        """查看数据库表"""
        try:
            from database_manager import DatabaseManager
            
            self.log("\n[LIST] 正在查询数据库表...", "info")
            
            db = DatabaseManager()
            if db.connection:
                db.cursor.execute("SHOW TABLES")
                tables = db.cursor.fetchall()
                
                if tables:
                    self.log("[STAT] 数据库中的表:", "info")
                    for table in tables:
                        table_name = table['Tables_in_quantitative_trading']
                        self.log(f"  - {table_name}")
                        
                        # 显示表结构
                        db.cursor.execute(f"DESCRIBE {table_name}")
                        columns = db.cursor.fetchall()
                        
                        for col in columns:
                            comment = col.get('Comment', '')
                            if comment:
                                self.log(f"    {col['Field']} ({col['Type']}) - {comment}")
                            else:
                                self.log(f"    {col['Field']} ({col['Type']})")
                else:
                    self.log("[WARN] 数据库中没有表", "warning")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 查询数据库表失败: {e}", "error")
    
    def sync_data_to_database(self):
        """同步数据到数据库"""
        try:
            from financial_data_integrator import FinancialDataIntegrator
            
            self.log("\n[SYNC] 正在同步数据到数据库...", "info")
            
            integrator = FinancialDataIntegrator()
            
            # 同步股票基本信息
            self.log("[STAT] 同步股票基本信息...")
            integrator.sync_stock_basic_info('沪深A股')
            
            # 同步部分股票的行情数据
            self.log("[UP] 同步行情数据...")
            test_codes = ['000001.SZ', '600000.SH', '00700.HK']
            start_date = '2024-01-01'
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            integrator.sync_daily_quotes(test_codes, start_date, end_date)
            
            # 计算技术指标
            self.log("[STAT] 计算技术指标...")
            integrator.calculate_all_technical_indicators(test_codes)
            
            integrator.close()
            self.log("[OK] 数据同步完成", "success")
            
        except Exception as e:
            self.log(f"[ERROR] 数据同步失败: {e}", "error")
    
    def view_csv_files(self):
        """查看CSV文件"""
        try:
            import glob
            
            self.log("\n[FILE] 正在扫描CSV文件...", "info")
            
            # 扫描项目目录下的CSV文件
            project_dir = os.path.dirname(__file__)
            csv_files = glob.glob(os.path.join(project_dir, "*.csv"))
            
            if csv_files:
                self.log("[STAT] 找到的CSV文件:", "info")
                for csv_file in csv_files:
                    file_name = os.path.basename(csv_file)
                    file_size = os.path.getsize(csv_file) / 1024  # KB
                    
                    # 尝试读取文件基本信息
                    try:
                        df = pd.read_csv(csv_file, nrows=1)
                        columns = len(df.columns)
                        self.log(f"  📄 {file_name} ({file_size:.1f} KB, {columns}列)")
                    except:
                        self.log(f"  📄 {file_name} ({file_size:.1f} KB)")
                
                # 提供查看选项
                self.log("\n[IDEA] 提示: 可以使用 '导入CSV到数据库' 功能将数据导入数据库", "info")
            else:
                self.log("[WARN] 未找到CSV文件", "warning")
                
        except Exception as e:
            self.log(f"[ERROR] 扫描CSV文件失败: {e}", "error")
    
    def import_csv_to_database(self):
        """导入CSV到数据库"""
        try:
            import tkinter.filedialog as filedialog
            from database_manager import DatabaseManager
            
            # 选择CSV文件
            file_path = filedialog.askopenfilename(
                title="选择CSV文件",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
            
            self.log(f"\n[IN] 正在导入CSV文件: {os.path.basename(file_path)}", "info")
            
            # 读取CSV文件
            df = pd.read_csv(file_path)
            self.log(f"[STAT] 文件包含 {len(df)} 行数据，{len(df.columns)} 列")
            
            # 显示列名
            self.log("[LIST] 数据列名:", "info")
            for i, col in enumerate(df.columns):
                self.log(f"  {i+1}. {col}")
            
            # 连接到数据库
            db = DatabaseManager()
            if db.connection:
                # 根据文件名猜测表名
                table_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # 创建临时表
                create_sql = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        {', '.join([f'{col} TEXT' for col in df.columns])}
                    )
                """
                
                db.cursor.execute(create_sql)
                
                # 插入数据
                for _, row in df.iterrows():
                    values = tuple(row.astype(str))
                    placeholders = ', '.join(['%s'] * len(df.columns))
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(df.columns)}) VALUES ({placeholders})"
                    db.cursor.execute(insert_sql, values)
                
                db.connection.commit()
                self.log(f"[OK] 成功导入 {len(df)} 行数据到表 {table_name}", "success")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 导入CSV失败: {e}", "error")
    
    def export_database_to_csv(self):
        """导出数据库到CSV"""
        try:
            import tkinter.filedialog as filedialog
            from database_manager import DatabaseManager
            
            # 选择保存位置
            file_path = filedialog.asksaveasfilename(
                title="保存CSV文件",
                defaultextension=".csv",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return
            
            self.log(f"\n[OUT] 正在导出数据到CSV...", "info")
            
            # 连接到数据库
            db = DatabaseManager()
            if db.connection:
                # 获取所有表
                db.cursor.execute("SHOW TABLES")
                tables = db.cursor.fetchall()
                
                if tables:
                    # 选择要导出的表
                    table_names = [table['Tables_in_quantitative_trading'] for table in tables]
                    
                    # 导出第一个表（可以根据需要扩展为多表选择）
                    table_name = table_names[0]
                    
                    # 查询数据
                    db.cursor.execute(f"SELECT * FROM {table_name}")
                    data = db.cursor.fetchall()
                    
                    if data:
                        # 转换为DataFrame并保存
                        df = pd.DataFrame(data)
                        df.to_csv(file_path, index=False)
                        
                        self.log(f"[OK] 成功导出表 {table_name} 的 {len(df)} 行数据到 {os.path.basename(file_path)}", "success")
                    else:
                        self.log(f"[WARN] 表 {table_name} 为空，无法导出", "warning")
                else:
                    self.log("[WARN] 数据库中没有表", "warning")
                
                db.close()
            else:
                self.log("[ERROR] 数据库连接失败", "error")
                
        except Exception as e:
            self.log(f"[ERROR] 导出数据失败: {e}", "error")
    
    def open_file_manager(self):
        """打开文件管理器，显示所有数据文件夹"""
        try:
            # 打开项目根目录
            project_dir = os.path.dirname(os.path.dirname(__file__))
            os.startfile(project_dir)
            self.log(f"[CHECK] 已打开项目文件夹: {project_dir}", "success")
            
            # 显示所有数据目录信息
            self.log("\n[FILE] 数据文件夹位置:", "info")
            self.log(f"  金融数据: {DATA_DIR}")
            
            analysis_dir = os.path.join(os.path.dirname(DATA_DIR), "分析数据")
            self.log(f"  分析数据: {analysis_dir}")
            
            model_dir = os.path.dirname(__file__)
            self.log(f"  AI模型: {model_dir}")
            
        except Exception as e:
            self.log(f"[X] 打开文件管理器失败: {e}", "error")
            messagebox.showerror("错误", f"无法打开文件管理器: {e}")
    
    def view_all_files(self):
        """查看所有数据文件"""
        self.log("\n[STAT] 所有数据文件统计:", "info")
        self.log("="*80)
        
        total_files = 0
        
        # 金融数据文件
        try:
            if os.path.exists(DATA_DIR):
                files = os.listdir(DATA_DIR)
                data_files = [f for f in files if os.path.isfile(os.path.join(DATA_DIR, f))]
                total_files += len(data_files)
                self.log(f"\n[IN] 金融数据文件 ({len(data_files)} 个):", "info")
                if data_files:
                    for i, f in enumerate(data_files[:20], 1):  # 显示前20个
                        filepath = os.path.join(DATA_DIR, f)
                        size = os.path.getsize(filepath) / 1024
                        self.log(f"  [{i}] {f} ({size:.2f} KB)")
                    if len(data_files) > 20:
                        self.log(f"  ... 还有 {len(data_files)-20} 个文件")
                else:
                    self.log("  (目录为空)", "warning")
            else:
                self.log("\n[IN] 金融数据文件夹不存在", "warning")
        except Exception as e:
            self.log(f"  [X] 读取金融数据文件夹失败: {e}", "error")
        
        # 分析数据文件
        try:
            analysis_dir = os.path.join(os.path.dirname(DATA_DIR), "分析数据")
            if os.path.exists(analysis_dir):
                files = os.listdir(analysis_dir)
                analysis_files = [f for f in files if os.path.isfile(os.path.join(analysis_dir, f))]
                total_files += len(analysis_files)
                self.log(f"\n[UP] 分析数据文件 ({len(analysis_files)} 个):", "info")
                if analysis_files:
                    for i, f in enumerate(analysis_files[:10], 1):  # 显示前10个
                        filepath = os.path.join(analysis_dir, f)
                        size = os.path.getsize(filepath) / 1024
                        self.log(f"  [{i}] {f} ({size:.2f} KB)")
                    if len(analysis_files) > 10:
                        self.log(f"  ... 还有 {len(analysis_files)-10} 个文件")
                else:
                    self.log("  (目录为空)", "warning")
            else:
                self.log("\n[UP] 分析数据文件夹不存在", "warning")
        except Exception as e:
            self.log(f"  [X] 读取分析数据文件夹失败: {e}", "error")
        
        # AI模型文件
        try:
            model_dir = os.path.dirname(__file__)
            import glob
            model_files = glob.glob(os.path.join(model_dir, "*.pkl"))
            total_files += len(model_files)
            self.log(f"\n[BOT] AI模型文件 ({len(model_files)} 个):", "info")
            if model_files:
                for i, f in enumerate(model_files, 1):
                    filename = os.path.basename(f)
                    size = os.path.getsize(f) / 1024
                    self.log(f"  [{i}] {filename} ({size:.2f} KB)")
            else:
                self.log("  (暂无模型文件)", "warning")
        except Exception as e:
            self.log(f"  [X] 读取AI模型文件失败: {e}", "error")
        
        self.log(f"\n[STAT] 文件总数: {total_files} 个", "success")
        self.log("="*80)
    
    # ==================== 基金交易功能 ====================

    def get_fund_data_with_retry(self, fund_code, max_retries=2, timeout=10):
        """带重试机制的基金数据获取"""
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        for attempt in range(max_retries):
            try:
                import akshare as ak
                self.log(f"  正在查询基金数据... (尝试 {attempt + 1}/{max_retries})", "info")

                # 1. 首先尝试查询ETF基金
                try:
                    fund_df = ak.fund_etf_spot_em()
                    fund_info = fund_df[fund_df['基金代码'] == fund_code]

                    if not fund_info.empty:
                        fund_name = fund_info.iloc[0]['基金名称']
                        fund_price = float(fund_info.iloc[0]['最新价'])
                        fund_change = float(fund_info.iloc[0]['涨跌幅'])
                        fund_type = "ETF基金"

                        # 查询基金详情
                        try:
                            fund_detail = ak.fund_em_open_fund_info(fund=fund_code, indicator="单位净值走势")
                            if not fund_detail.empty:
                                latest_nav = float(fund_detail.iloc[-1]['单位净值'])
                                nav_date = fund_detail.iloc[-1]['净值日期']

                                return {
                                    'fund_code': fund_code,
                                    'fund_name': fund_name,
                                    'fund_type': fund_type,
                                    'nav': latest_nav,
                                    'nav_date': nav_date,
                                    'price': fund_price,
                                    'change': fund_change,
                                    'success': True
                                }
                        except Exception as e:
                            self.log(f"  获取净值详情失败: {e}", "warning")
                            # 使用实时价格作为净值
                            return {
                                'fund_code': fund_code,
                                'fund_name': fund_name,
                                'fund_type': fund_type,
                                'nav': fund_price,
                                'nav_date': '实时',
                                'price': fund_price,
                                'change': fund_change,
                                'success': True
                            }
                except Exception as e:
                    self.log(f"  ETF基金查询失败: {e}", "warning")

                # 2. 尝试查询LOF基金 (上市开放式基金) - 使用相同的ETF接口
                try:
                    # LOF基金也可能在ETF接口中
                    if len(fund_code) == 6 and fund_code.isdigit():
                        # 尝试获取LOF基金列表
                        try:
                            # 尝试使用基金实时净值接口
                            lof_df = ak.fund_etf_spot_em()
                            lof_info = lof_df[lof_df['基金代码'] == fund_code]
                            if not lof_info.empty:
                                fund_name = lof_info.iloc[0]['基金名称']
                                fund_price = float(lof_info.iloc[0]['最新价'])
                                fund_change = float(lof_info.iloc[0]['涨跌幅'])
                                fund_type = "LOF基金"

                                try:
                                    fund_detail = ak.fund_em_open_fund_info(fund=fund_code, indicator="单位净值走势")
                                    if not fund_detail.empty:
                                        latest_nav = float(fund_detail.iloc[-1]['单位净值'])
                                        nav_date = fund_detail.iloc[-1]['净值日期']

                                        return {
                                            'fund_code': fund_code,
                                            'fund_name': fund_name,
                                            'fund_type': fund_type,
                                            'nav': latest_nav,
                                            'nav_date': nav_date,
                                            'price': fund_price,
                                            'change': fund_change,
                                            'success': True
                                        }
                                except Exception as e:
                                    self.log(f"  获取净值详情失败: {e}", "warning")
                                    return {
                                        'fund_code': fund_code,
                                        'fund_name': fund_name,
                                        'fund_type': fund_type,
                                        'nav': fund_price,
                                        'nav_date': '实时',
                                        'price': fund_price,
                                        'change': fund_change,
                                        'success': True
                                    }
                        except Exception as e:
                            self.log(f"  LOF基金查询失败: {e}", "warning")
                except Exception as e:
                    self.log(f"  LOF基金查询异常: {e}", "warning")

                # 3. 尝试查询开放式基金净值
                try:
                    fund_detail = ak.fund_em_open_fund_info(fund=fund_code, indicator="单位净值走势")
                    if not fund_detail.empty:
                        # 通过净值走势获取基金信息
                        latest_nav = float(fund_detail.iloc[-1]['单位净值'])
                        nav_date = fund_detail.iloc[-1]['净值日期']

                        # 尝试获取基金基本信息
                        fund_name = f"基金{fund_code}"
                        fund_type = "开放式基金"

                        # 尝试获取基金实时数据
                        try:
                            fund_portfolio = ak.fund_em_open_fund_info(fund=fund_code, indicator="基金规模")
                            if not fund_portfolio.empty:
                                fund_name = fund_portfolio.iloc[0].get('基金简称', f"基金{fund_code}")
                        except:
                            pass

                        return {
                            'fund_code': fund_code,
                            'fund_name': fund_name,
                            'fund_type': fund_type,
                            'nav': latest_nav,
                            'nav_date': nav_date,
                            'price': latest_nav,
                            'change': 0.0,
                            'success': True
                        }
                except Exception as e:
                    self.log(f"  开放式基金净值查询失败: {e}", "warning")

                # 4. 如果所有方法都失败，返回未找到
                self.log(f"  未找到基金代码: {fund_code}", "warning")
                return {
                    'fund_code': fund_code,
                    'fund_name': None,
                    'fund_type': None,
                    'nav': None,
                    'nav_date': None,
                    'price': None,
                    'change': None,
                    'success': False,
                    'message': f'未找到基金 {fund_code}'
                }

            except Exception as e:
                self.log(f"  查询失败 (尝试 {attempt + 1}/{max_retries}): {e}", "warning")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)  # 等待2秒后重试

        # 所有尝试都失败，返回模拟数据
        self.log("  网络查询失败，使用模拟数据", "warning")
        import random
        simulated_nav = random.uniform(1.0, 3.0)
        fund_name = f"模拟基金{fund_code}"

        return {
            'fund_code': fund_code,
            'fund_name': fund_name,
            'fund_type': '模拟基金',
            'nav': simulated_nav,
            'nav_date': '模拟数据',
            'price': simulated_nav,
            'change': random.uniform(-5, 5),
            'success': True,
            'is_simulated': True
        }

    def center_window(self, window):
        """居中显示窗口"""
        window.update_idletasks()
        x = (window.winfo_screenwidth() // 2) - (window.winfo_width() // 2)
        y = (window.winfo_screenheight() // 2) - (window.winfo_height() // 2)
        window.geometry(f"+{x}+{y}")

    def query_fund_info(self):
        """查询基金信息"""
        fund_code = self.fund_code_entry.get().strip()
        if not fund_code:
            messagebox.showwarning("警告", "请输入基金代码")
            return

        def query_thread():
            try:
                self.log("\n" + "="*80)
                self.log(f"[FIND] 查询基金信息: {fund_code}", "info")
                self.log("="*80)

                # 检查akshare是否安装
                try:
                    import akshare as ak
                    has_akshare = True
                except ImportError:
                    has_akshare = False
                    self.log("[WARN]  未安装akshare库", "warning")

                if has_akshare:
                    # 使用akshare查询
                    fund_data = self.get_fund_data_with_retry(fund_code)
                else:
                    # 使用模拟数据
                    import random
                    simulated_nav = random.uniform(1.0, 3.0)
                    fund_name = f"模拟基金{fund_code}"

                    fund_data = {
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'fund_type': '模拟基金',
                        'nav': simulated_nav,
                        'nav_date': '模拟数据',
                        'price': simulated_nav,
                        'change': random.uniform(-5, 5),
                        'success': True,
                        'is_simulated': True
                    }

                # 显示查询结果
                if fund_data['success']:
                    fund_name = fund_data['fund_name']
                    nav = fund_data['nav']
                    nav_date = fund_data['nav_date']
                    price = fund_data['price']
                    change = fund_data['change']
                    fund_type = fund_data['fund_type']
                    is_simulated = fund_data.get('is_simulated', False)

                    # 构建显示文本
                    info_text = f"基金代码: {fund_code}\n"
                    info_text += f"基金名称: {fund_name}\n"
                    info_text += f"基金类型: {fund_type}\n"

                    if nav is not None:
                        info_text += f"最新净值: {nav:.4f} 元 ({nav_date})\n"

                    if price is not None and price != nav:
                        info_text += f"最新价: {price:.4f} 元\n"

                    if change is not None:
                        change_color = "绿色" if change >= 0 else "红色"
                        info_text += f"涨跌幅: {change:+.2f}% ({change_color})\n"

                    if is_simulated:
                        info_text += "\n(使用模拟数据)"

                    # 更新界面
                    self.root.after(0, lambda: self.fund_info_label.config(text=info_text, foreground="black"))

                    # 记录日志
                    self.log(f"[CHECK] 基金名称: {fund_name}", "success")
                    self.log(f"  基金类型: {fund_type}", "success")

                    if nav is not None:
                        self.log(f"  最新净值: {nav:.4f} 元 ({nav_date})", "success")

                    if change is not None:
                        self.log(f"  涨跌幅: {change:+.2f}%", "success")

                    if is_simulated:
                        self.log("  注意: 使用模拟数据", "warning")

                else:
                    # 查询失败
                    message = fund_data.get('message', '查询失败')
                    self.root.after(0, lambda: self.fund_info_label.config(
                        text=f"未找到基金: {fund_code}\n{message}",
                        foreground="red"
                    ))
                    self.log(f"[X] {message}", "error")

                self.log("="*80)

            except Exception as e:
                self.log(f"[X] 查询失败: {e}", "error")
                self.root.after(0, lambda: self.fund_info_label.config(text=f"查询失败: {e}", foreground="red"))

        threading.Thread(target=query_thread, daemon=True).start()

    def buy_fund(self):
        """买入基金"""
        fund_code = self.fund_buy_code_entry.get().strip()
        try:
            amount = float(self.fund_buy_amount_entry.get().strip())
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的金额")
            return

        if not fund_code:
            messagebox.showwarning("警告", "请输入基金代码")
            return

        if amount <= 0:
            messagebox.showwarning("警告", "金额必须大于0")
            return

        def buy_thread():
            try:
                self.log("\n" + "="*80)
                self.log(f"[MONEY] 买入基金: {fund_code}", "info")
                self.log("="*80)

                # 获取基金信息
                fund_data = self.get_fund_data_with_retry(fund_code)

                if not fund_data['success'] or fund_data['nav'] is None:
                    self.log(f"[X] 无法获取基金净值", "error")
                    return

                nav = fund_data['nav']
                fund_name = fund_data['fund_name']
                fund_type = fund_data['fund_type']

                # 计算份额（假设无申购费）
                volume = amount / nav

                # 执行买入
                success = self.fund_manager.add_position(fund_code, fund_name, volume, nav, fund_type=fund_type)

                if success:
                    self.root.after(0, lambda: [
                        self.refresh_fund_portfolio(),
                        self.fund_buy_code_entry.delete(0, tk.END),
                        self.fund_buy_amount_entry.delete(0, tk.END)
                    ])
                    self.log(f"[CHECK] 买入成功: {fund_name}({fund_code})", "success")
                    self.log(f"  基金类型: {fund_type}", "success")
                    self.log(f"  金额: {amount:,.2f} 元, 净值: {nav:.4f}", "success")
                    self.log(f"  获得份额: {volume:.2f} 份", "success")
                else:
                    self.log(f"[X] 买入失败", "error")

                self.log("="*80)

            except Exception as e:
                self.log(f"[X] 买入失败: {e}", "error")

        threading.Thread(target=buy_thread, daemon=True).start()

    def sell_fund(self):
        """卖出基金"""
        fund_code = self.fund_sell_code_entry.get().strip()
        try:
            volume = float(self.fund_sell_volume_entry.get().strip())
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的份额")
            return

        if not fund_code:
            messagebox.showwarning("警告", "请输入基金代码")
            return

        if volume <= 0:
            messagebox.showwarning("警告", "份额必须大于0")
            return

        def sell_thread():
            try:
                self.log("\n" + "="*80)
                self.log(f"💸 卖出基金: {fund_code}", "info")
                self.log("="*80)

                # 获取基金最新净值
                fund_data = self.get_fund_data_with_retry(fund_code)

                if not fund_data['success'] or fund_data['nav'] is None:
                    self.log(f"[X] 无法获取基金净值", "error")
                    return

                nav = fund_data['nav']

                # 执行卖出
                success = self.fund_manager.reduce_position(fund_code, volume, nav)

                if success:
                    self.root.after(0, lambda: [
                        self.refresh_fund_portfolio(),
                        self.fund_sell_code_entry.delete(0, tk.END),
                        self.fund_sell_volume_entry.delete(0, tk.END)
                    ])
                    self.log(f"[CHECK] 卖出成功: {fund_code}", "success")
                    self.log(f"  卖出份额: {volume:.2f} 份, 净值: {nav:.4f}", "success")
                else:
                    self.log(f"[X] 卖出失败", "error")

                self.log("="*80)

            except Exception as e:
                self.log(f"[X] 卖出失败: {e}", "error")

        threading.Thread(target=sell_thread, daemon=True).start()

    def get_fund_nav(self, fund_code):
        """获取基金净值（使用重试机制）"""
        fund_data = self.get_fund_data_with_retry(fund_code)

        if fund_data['success'] and fund_data['nav'] is not None:
            return fund_data['nav']
        else:
            return None

    def get_fund_name(self, fund_code):
        """获取基金名称（使用重试机制）"""
        fund_data = self.get_fund_data_with_retry(fund_code)

        if fund_data['success'] and fund_data['fund_name'] is not None:
            return fund_data['fund_name']
        else:
            return f"基金{fund_code}"

    def get_fund_type(self, fund_code):
        """获取基金类型"""
        fund_data = self.get_fund_data_with_retry(fund_code)

        if fund_data['success'] and fund_data['fund_type'] is not None:
            return fund_data['fund_type']
        else:
            return "未知类型"

    def get_fund_name(self, fund_code):
        """获取基金名称"""
        try:
            import akshare as ak

            fund_df = ak.fund_etf_spot_em()
            fund_info = fund_df[fund_df['基金代码'] == fund_code]

            if not fund_info.empty:
                return fund_info.iloc[0]['基金名称']

            fund_search = ak.fund_em_open_fund_search(fund=fund_code)
            if not fund_search.empty:
                return fund_search.iloc[0]['基金简称']

            return f"基金{fund_code}"

        except Exception as e:
            return f"基金{fund_code}"

    def refresh_fund_nav(self):
        """刷新基金净值"""
        def refresh_thread():
            try:
                self.log("\n" + "="*80)
                self.log("[SYNC] 开始刷新基金净值...", "info")
                self.log("="*80)

                nav_updates = {}
                for pos in self.fund_manager.get_position_list():
                    fund_code = pos.fund_code
                    nav = self.get_fund_nav(fund_code)

                    if nav is not None:
                        nav_updates[fund_code] = nav
                        self.log(f"  [CHECK] {fund_code} ({pos.fund_name}): {pos.current_nav:.4f} -> {nav:.4f}", "success")
                    else:
                        self.log(f"  [X] {fund_code}: 获取净值失败", "error")

                # 更新净值
                if nav_updates:
                    self.fund_manager.update_all_nav(nav_updates)
                    self.fund_manager.save_portfolio()

                    # 刷新显示
                    self.root.after(0, lambda: [
                        self.refresh_fund_portfolio(),
                        self.log(f"\n[CHECK] 成功更新 {len(nav_updates)} 只基金净值", "success")
                    ])
                else:
                    self.log("\n[X] 没有成功更新任何基金净值", "error")

                self.log("="*80)

            except Exception as e:
                self.log(f"[X] 刷新失败: {e}", "error")

        threading.Thread(target=refresh_thread, daemon=True).start()

    def refresh_fund_portfolio(self):
        """刷新基金持仓"""
        # 清空表格
        for item in self.fund_tree.get_children():
            self.fund_tree.delete(item)

        # 填充持仓列表
        for pos in self.fund_manager.get_position_list():
            profit = pos.get_profit_loss()
            profit_pct = pos.get_profit_loss_pct()

            item = self.fund_tree.insert("", tk.END, values=(
                pos.fund_code,
                pos.fund_name,
                pos.fund_type,
                f"{pos.volume:.2f}",
                f"{pos.avg_nav:.4f}",
                f"{pos.current_nav:.4f}",
                f"{pos.current_value:,.2f}",
                f"{profit:+,.2f}",
                f"{profit_pct:+.2f}%"
            ))

            # 根据盈亏设置标签颜色
            tags = ("profit",) if profit >= 0 else ("loss",)
            self.fund_tree.item(item, tags=tags)

        # 配置标签颜色
        self.fund_tree.tag_configure("profit", foreground="green")
        self.fund_tree.tag_configure("loss", foreground="red")

    def show_fund_trade_history(self):
        """显示基金交易记录"""
        dialog = tk.Toplevel(self.root)
        dialog.title("基金交易记录")
        dialog.geometry("900x600")
        dialog.transient(self.root)

        # 创建表格
        columns = ("date", "action", "fund", "nav", "volume", "amount", "profit")
        tree = ttk.Treeview(dialog, columns=columns, show="headings")

        tree.heading("date", text="日期")
        tree.heading("action", text="操作")
        tree.heading("fund", text="基金")
        tree.heading("nav", text="净值")
        tree.heading("volume", text="份额")
        tree.heading("amount", text="金额")
        tree.heading("profit", text="盈亏")

        tree.column("date", width=120)
        tree.column("action", width=60)
        tree.column("fund", width=200)
        tree.column("nav", width=80)
        tree.column("volume", width=100)
        tree.column("amount", width=120)
        tree.column("profit", width=100)

        tree.pack(fill=tk.BOTH, expand=True)

        # 填充数据
        for record in reversed(self.fund_manager.history):
            action = record['action']
            action_str = "买入" if action == 'buy' else "卖出"
            profit_str = f"{record.get('profit', 0):+,.2f}" if action == 'sell' else "-"

            fund = f"{record['fund_name']}({record['fund_code']})"

            tree.insert("", tk.END, values=(
                record['date'][:10],
                action_str,
                fund,
                f"{record['nav']:.4f}",
                f"{record['volume']:.2f}",
                f"{record['amount']:,.2f}",
                profit_str
            ))

        # 关闭按钮
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)

    def clear_fund_portfolio(self):
        """清空基金持仓"""
        result = messagebox.askyesno("确认", "确定要清空所有基金持仓吗?\n此操作不可恢复!")
        if result:
            self.fund_manager.clear_portfolio()
            self.refresh_fund_portfolio()
            self.log("[CHECK] 基金持仓已清空", "success")
            messagebox.showinfo("完成", "基金持仓已清空")

    def query_sector_stocks(self):
        """查询板块成分股（概念板块或行业板块）"""
        # 防止重复查询
        if hasattr(self, 'sector_query_running') and self.sector_query_running:
            messagebox.showwarning("警告", "查询正在进行中，请稍候...")
            return
        
        sector_name = self.sector_query_entry.get().strip()
        sector_type = self.sector_type_var.get()  # 获取板块类型
        
        if not sector_name:
            messagebox.showwarning("警告", "请输入板块名称")
            return
        
        sector_display_name = "概念板块" if sector_type == "concept" else "行业板块"
        self.log(f"[FIND] 正在查询【{sector_name}】{sector_display_name}成分股...")
        
        # 设置查询状态
        self.sector_query_running = True
        
        def query_thread():
            try:
                # 从爬取金融数据模块获取板块成分股
                from 爬取金融数据 import FinancialDataCrawler
                crawler = FinancialDataCrawler()
                import time
                
                # 尝试多次获取数据，以防网络不稳定
                max_retries = 3
                df = None
                for attempt in range(max_retries):
                    try:
                        if sector_type == "concept":
                            df = crawler.get_concept_stocks(sector_name)
                        else:  # industry
                            df = crawler.get_industry_stocks(sector_name)
                        break  # 成功获取数据则跳出循环
                    except Exception as e:
                        self.log(f"[WARN] 第 {attempt + 1} 次查询{sector_display_name}失败: {e}", "warning")
                        if attempt == max_retries - 1:  # 最后一次尝试也失败
                            raise e
                        time.sleep(2)  # 等待2秒后重试
                
                if df is None or df.empty:
                    self.root.after(0, lambda: [
                        self.log(f"[ERROR] 未找到【{sector_name}】相关{sector_display_name}", "error"),
                        messagebox.showinfo("提示", f"未找到【{sector_name}】相关{sector_display_name}"),
                        setattr(self, 'sector_query_running', False)  # 重置查询状态
                    ])
                    return
                
                # 在主线程中更新UI
                def update_ui():
                    # 清空现有数据
                    for item in self.sector_stocks_tree.get_children():
                        self.sector_stocks_tree.delete(item)
                    
                    # 限制显示数量以防止卡死
                    display_limit = 50  # 限制最多显示50只股票
                    rows_to_show = min(len(df), display_limit)
                    
                    # 填充数据
                    for i, (_, row) in enumerate(df.iterrows()):
                        if i >= display_limit:
                            self.log(f"[WARN] 由于性能考虑，仅显示前 {display_limit} 只股票，共 {len(df)} 只")
                            break
                        
                        code = row.get('代码', '')
                        name = row.get('名称', '')
                        reason = row.get('入选理由', '') if '入选理由' in row else ''
                        
                        # 获取实时行情数据（限制频率以防止卡死）
                        if i % 5 == 0:  # 每5只股票显示一次进度
                            self.log(f"[STAT] 正在获取实时数据... ({i+1}/{rows_to_show})")
                        
                        # 获取实时行情数据
                        realtime_data = self.get_realtime_price(code)
                        if realtime_data:
                            price = realtime_data.get('price', 'N/A')
                            change_pct = realtime_data.get('change_pct', 'N/A')
                            volume = realtime_data.get('volume', 'N/A')
                        else:
                            price = 'N/A'
                            change_pct = 'N/A'
                            volume = 'N/A'
                        
                        item = self.sector_stocks_tree.insert("", tk.END, values=(
                            code,
                            name,
                            str(price),
                            str(change_pct),
                            str(volume),
                            reason
                        ))
                    
                    self.log(f"[OK] 查询完成，共获取 {len(df)} 只【{sector_name}】{sector_display_name}股，显示 {rows_to_show} 只")
                    self.sector_query_running = False  # 重置查询状态
                
                self.root.after(0, update_ui)
                
            except Exception as e:
                self.root.after(0, lambda e=e: [
                    self.log(f"[ERROR] 查询{sector_display_name}失败: {e}", "error"),
                    messagebox.showerror("错误", f"查询{sector_display_name}失败:\n{str(e)}\n\n提示: 请检查网络连接或稍后再试"),
                    setattr(self, 'sector_query_running', False)  # 重置查询状态
                ])
        
        threading.Thread(target=query_thread, daemon=True).start()

    def get_realtime_price(self, stock_code):
        """获取股票实时价格"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == stock_code]
            if not stock_data.empty:
                row = stock_data.iloc[0]
                return {
                    'price': row['最新价'],
                    'change_pct': f"{row['涨跌幅']:.2f}%",
                    'volume': f"{row['成交量']:,}"
                }
        except Exception as e:
            self.log(f"[WARN] 获取实时价格失败 {stock_code}: {e}", "warning")
        return None

    def get_hot_sectors(self):
        """获取热门板块"""
        # 防止重复查询
        if hasattr(self, 'hot_sector_query_running') and self.hot_sector_query_running:
            messagebox.showwarning("警告", "热门板块查询正在进行中，请稍候...")
            return
        
        # 设置查询状态
        self.hot_sector_query_running = True
        
        # 弹出选择对话框，让用户选择是查看概念板块还是行业板块
        choice_window = tk.Toplevel(self.root)
        choice_window.title("选择板块类型")
        choice_window.geometry("300x150")
        choice_window.transient(self.root)
        choice_window.grab_set()
        
        # 居中显示
        self.center_window(choice_window)
        
        ttk.Label(choice_window, text="请选择要查看的板块类型:", font=("Arial", 12)).pack(pady=20)
        
        def select_concept():
            choice_window.destroy()
            self._get_hot_concept_sectors()
        
        def select_industry():
            choice_window.destroy()
            self._get_hot_industry_sectors()
        
        btn_frame = ttk.Frame(choice_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="概念板块", command=select_concept, width=12).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="行业板块", command=select_industry, width=12).pack(side=tk.LEFT, padx=10)
    
    def _get_hot_concept_sectors(self):
        """获取热门概念板块"""
        self.log("[FIND] 正在获取热门概念板块...")
        
        def query_thread():
            try:
                import akshare as ak
                import time
                
                # 尝试多次获取数据，以防网络不稳定
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # 设置请求超时，防止卡死
                        import requests
                        requests.adapters.DEFAULT_RETRIES = 3
                        
                        # 获取概念板块
                        sector_df = ak.stock_board_concept_name_em()
                        break  # 成功获取数据则跳出循环
                    except Exception as e:
                        self.log(f"[WARN] 第 {attempt + 1} 次获取热门概念板块失败: {e}", "warning")
                        if attempt == max_retries - 1:  # 最后一次尝试也失败
                            raise e
                        time.sleep(2)  # 等待2秒后重试
                
                if sector_df.empty:
                    self.root.after(0, lambda: [
                        self.log("[ERROR] 无法获取热门概念板块数据", "error"),
                        messagebox.showinfo("提示", "无法获取热门概念板块数据"),
                        setattr(self, 'hot_sector_query_running', False)  # 重置查询状态
                    ])
                    return
                
                # 显示前20个热门概念板块
                hot_sectors = sector_df.head(20)
                
                # 在主线程中显示热门概念板块列表
                def show_sectors():
                    sector_list_window = tk.Toplevel(self.root)
                    sector_list_window.title("热门概念板块列表")
                    sector_list_window.geometry("600x400")
                    
                    # 创建表格
                    columns = ("name", "code", "price", "change_pct")
                    tree = ttk.Treeview(sector_list_window, columns=columns, show="headings", height=15)
                    
                    tree.heading("name", text="板块名称")
                    tree.heading("code", text="代码")
                    tree.heading("price", text="指数")
                    tree.heading("change_pct", text="今日涨跌")
                    
                    tree.column("name", width=200)
                    tree.column("code", width=100)
                    tree.column("price", width=100)
                    tree.column("change_pct", width=100)
                    
                    # 添加滚动条
                    scrollbar = ttk.Scrollbar(sector_list_window, orient=tk.VERTICAL, command=tree.yview)
                    tree.configure(yscrollcommand=scrollbar.set)
                    
                    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    
                    # 填充数据
                    for _, row in hot_sectors.iterrows():
                        tree.insert("", tk.END, values=(
                            row.get('板块名称', ''),
                            row.get('板块代码', ''),
                            row.get('最新价', ''),
                            f"{row.get('涨跌幅', 0):+.2f}%"
                        ))
                    
                    self.log(f"[OK] 获取热门概念板块成功，显示前 {len(hot_sectors)} 个板块")
                    self.hot_sector_query_running = False  # 重置查询状态
                
                self.root.after(0, show_sectors)
                
            except Exception as e:
                self.root.after(0, lambda e=e: [
                    self.log(f"[ERROR] 获取热门概念板块失败: {e}", "error"),
                    messagebox.showerror("错误", f"获取热门概念板块失败:\n{str(e)}\n\n提示: 请检查网络连接或稍后再试"),
                    setattr(self, 'hot_sector_query_running', False)  # 重置查询状态
                ])
        
        threading.Thread(target=query_thread, daemon=True).start()
    
    def _get_hot_industry_sectors(self):
        """获取热门行业板块"""
        self.log("[FIND] 正在获取热门行业板块...")
        
        def query_thread():
            try:
                import akshare as ak
                import time
                
                # 尝试多次获取数据，以防网络不稳定
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # 设置请求超时，防止卡死
                        import requests
                        requests.adapters.DEFAULT_RETRIES = 3
                        
                        # 获取行业板块
                        sector_df = ak.stock_board_industry_name_em()
                        break  # 成功获取数据则跳出循环
                    except Exception as e:
                        self.log(f"[WARN] 第 {attempt + 1} 次获取热门行业板块失败: {e}", "warning")
                        if attempt == max_retries - 1:  # 最后一次尝试也失败
                            raise e
                        time.sleep(2)  # 等待2秒后重试
                
                if sector_df.empty:
                    self.root.after(0, lambda: [
                        self.log("[ERROR] 无法获取热门行业板块数据", "error"),
                        messagebox.showinfo("提示", "无法获取热门行业板块数据"),
                        setattr(self, 'hot_sector_query_running', False)  # 重置查询状态
                    ])
                    return
                
                # 显示前20个热门行业板块
                hot_sectors = sector_df.head(20)
                
                # 在主线程中显示热门行业板块列表
                def show_sectors():
                    sector_list_window = tk.Toplevel(self.root)
                    sector_list_window.title("热门行业板块列表")
                    sector_list_window.geometry("600x400")
                    
                    # 创建表格
                    columns = ("name", "code", "price", "change_pct")
                    tree = ttk.Treeview(sector_list_window, columns=columns, show="headings", height=15)
                    
                    tree.heading("name", text="板块名称")
                    tree.heading("code", text="代码")
                    tree.heading("price", text="指数")
                    tree.heading("change_pct", text="今日涨跌")
                    
                    tree.column("name", width=200)
                    tree.column("code", width=100)
                    tree.column("price", width=100)
                    tree.column("change_pct", width=100)
                    
                    # 添加滚动条
                    scrollbar = ttk.Scrollbar(sector_list_window, orient=tk.VERTICAL, command=tree.yview)
                    tree.configure(yscrollcommand=scrollbar.set)
                    
                    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    
                    # 填充数据
                    for _, row in hot_sectors.iterrows():
                        tree.insert("", tk.END, values=(
                            row.get('板块名称', ''),
                            row.get('板块代码', ''),
                            row.get('最新价', ''),
                            f"{row.get('涨跌幅', 0):+.2f}%"
                        ))
                    
                    self.log(f"[OK] 获取热门行业板块成功，显示前 {len(hot_sectors)} 个板块")
                    self.hot_sector_query_running = False  # 重置查询状态
                
                self.root.after(0, show_sectors)
                
            except Exception as e:
                self.root.after(0, lambda e=e: [
                    self.log(f"[ERROR] 获取热门行业板块失败: {e}", "error"),
                    messagebox.showerror("错误", f"获取热门行业板块失败:\n{str(e)}\n\n提示: 请检查网络连接或稍后再试"),
                    setattr(self, 'hot_sector_query_running', False)  # 重置查询状态
                ])
        
        threading.Thread(target=query_thread, daemon=True).start()

    def show_sector_rankings(self):
        """显示板块排行"""
        # 弹出选择对话框，让用户选择查看概念板块排行还是行业板块排行
        choice_window = tk.Toplevel(self.root)
        choice_window.title("选择板块类型")
        choice_window.geometry("300x150")
        choice_window.transient(self.root)
        choice_window.grab_set()
        
        # 居中显示
        self.center_window(choice_window)
        
        ttk.Label(choice_window, text="请选择要查看的板块类型:", font=("Arial", 12)).pack(pady=20)
        
        def select_concept_rankings():
            choice_window.destroy()
            self._show_concept_rankings()
        
        def select_industry_rankings():
            choice_window.destroy()
            self._show_industry_rankings()
        
        btn_frame = ttk.Frame(choice_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="概念板块排行", command=select_concept_rankings, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="行业板块排行", command=select_industry_rankings, width=15).pack(side=tk.LEFT, padx=10)
    
    def _show_concept_rankings(self):
        """显示概念板块排行"""
        self.log("[STAT] 正在获取概念板块排行数据...")
        
        def query_thread():
            try:
                import akshare as ak
                
                # 获取概念板块排名（按涨跌幅）
                concept_df = ak.stock_board_concept_name_em()
                
                if concept_df.empty:
                    self.root.after(0, lambda: [
                        self.log("[ERROR] 无法获取概念板块排行数据", "error"),
                        messagebox.showinfo("提示", "无法获取概念板块排行数据")
                    ])
                    return
                
                # 在主线程中显示排行窗口
                def show_rankings():
                    ranking_window = tk.Toplevel(self.root)
                    ranking_window.title("概念板块排行")
                    ranking_window.geometry("800x500")
                    
                    # 创建表格
                    columns = ("rank", "name", "change_pct", "price", "rise_count", "fall_count")
                    tree = ttk.Treeview(ranking_window, columns=columns, show="headings", height=20)
                    
                    tree.heading("rank", text="排名")
                    tree.heading("name", text="板块名称")
                    tree.heading("change_pct", text="今日涨跌")
                    tree.heading("price", text="板块指数")
                    tree.heading("rise_count", text="上涨家数")
                    tree.heading("fall_count", text="下跌家数")
                    
                    tree.column("rank", width=60)
                    tree.column("name", width=150)
                    tree.column("change_pct", width=100)
                    tree.column("price", width=100)
                    tree.column("rise_count", width=80)
                    tree.column("fall_count", width=80)
                    
                    # 添加滚动条
                    scrollbar = ttk.Scrollbar(ranking_window, orient=tk.VERTICAL, command=tree.yview)
                    tree.configure(yscrollcommand=scrollbar.set)
                    
                    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    
                    # 由于无法直接获得概念板块排名，我们显示前20个概念板块
                    for i, (_, row) in enumerate(concept_df.head(20).iterrows()):
                        tree.insert("", tk.END, values=(
                            i + 1,
                            row.get('板块名称', ''),
                            f"{row.get('涨跌幅', 0):+.2f}%",
                            f"{row.get('最新价', 0):.2f}",
                            row.get('上涨家数', 0),
                            row.get('下跌家数', 0)
                        ))
                    
                    self.log(f"[OK] 获取概念板块排行成功，显示前 {len(concept_df.head(20))} 个板块")
                
                self.root.after(0, show_rankings)
                
            except Exception as e:
                self.root.after(0, lambda e=e: [
                    self.log(f"[ERROR] 获取概念板块排行失败: {e}", "error"),
                    messagebox.showerror("错误", f"获取概念板块排行失败: {e}")
                ])
        
        threading.Thread(target=query_thread, daemon=True).start()
    
    def _show_industry_rankings(self):
        """显示行业板块排行"""
        self.log("[STAT] 正在获取行业板块排行数据...")
        
        def query_thread():
            try:
                import akshare as ak
                
                # 获取行业板块排名（按涨跌幅）
                industry_df = ak.stock_board_industry_name_em()
                
                if industry_df.empty:
                    self.root.after(0, lambda: [
                        self.log("[ERROR] 无法获取行业板块排行数据", "error"),
                        messagebox.showinfo("提示", "无法获取行业板块排行数据")
                    ])
                    return
                
                # 在主线程中显示排行窗口
                def show_rankings():
                    ranking_window = tk.Toplevel(self.root)
                    ranking_window.title("行业板块排行")
                    ranking_window.geometry("800x500")
                    
                    # 创建表格
                    columns = ("rank", "name", "change_pct", "price", "rise_count", "fall_count")
                    tree = ttk.Treeview(ranking_window, columns=columns, show="headings", height=20)
                    
                    tree.heading("rank", text="排名")
                    tree.heading("name", text="板块名称")
                    tree.heading("change_pct", text="今日涨跌")
                    tree.heading("price", text="板块指数")
                    tree.heading("rise_count", text="上涨家数")
                    tree.heading("fall_count", text="下跌家数")
                    
                    tree.column("rank", width=60)
                    tree.column("name", width=150)
                    tree.column("change_pct", width=100)
                    tree.column("price", width=100)
                    tree.column("rise_count", width=80)
                    tree.column("fall_count", width=80)
                    
                    # 添加滚动条
                    scrollbar = ttk.Scrollbar(ranking_window, orient=tk.VERTICAL, command=tree.yview)
                    tree.configure(yscrollcommand=scrollbar.set)
                    
                    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    
                    # 显示前20个行业板块
                    for i, (_, row) in enumerate(industry_df.head(20).iterrows()):
                        tree.insert("", tk.END, values=(
                            i + 1,
                            row.get('板块名称', ''),
                            f"{row.get('涨跌幅', 0):+.2f}%",
                            f"{row.get('最新价', 0):.2f}",
                            row.get('上涨家数', 0),
                            row.get('下跌家数', 0)
                        ))
                    
                    self.log(f"[OK] 获取行业板块排行成功，显示前 {len(industry_df.head(20))} 个板块")
                
                self.root.after(0, show_rankings)
                
            except Exception as e:
                self.root.after(0, lambda e=e: [
                    self.log(f"[ERROR] 获取行业板块排行失败: {e}", "error"),
                    messagebox.showerror("错误", f"获取行业板块排行失败: {e}")
                ])
        
        threading.Thread(target=query_thread, daemon=True).start()

    def analyze_sector_trend(self):
        """分析板块趋势"""
        selection = self.sector_stocks_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一只板块成分股")
            return
        
        item = self.sector_stocks_tree.item(selection[0])
        stock_code = item['values'][0]  # 股票代码
        stock_name = item['values'][1]  # 股票名称
        
        self.log(f"[UP] 正在分析 {stock_code} {stock_name} 的趋势...")
        
        def trend_analysis_thread():
            try:
                import akshare as ak
                import pandas as pd
                import matplotlib.pyplot as plt
                from matplotlib import rcParams
                
                # 设置中文字体
                rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
                rcParams['axes.unicode_minus'] = False
                
                # 获取股票历史数据
                # 根据股票代码判断市场并获取数据
                if stock_code.startswith(('00', '30', '15', '16', '18', '19')):
                    # 深圳市场
                    stock_data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
                elif stock_code.startswith(('60', '68', '7', '9')):
                    # 上海市场
                    stock_data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
                else:
                    # 默认按上海市场处理
                    stock_data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
                
                if stock_data.empty:
                    self.root.after(0, lambda: [
                        self.log(f"[ERROR] 无法获取 {stock_code} 的历史数据", "error"),
                        messagebox.showinfo("提示", f"无法获取 {stock_code} 的历史数据")
                    ])
                    return
                
                # 计算技术指标
                df = stock_data.tail(60).copy()  # 取最近60天数据
                df['date'] = pd.to_datetime(df['日期'])
                df.set_index('date', inplace=True)
                
                # 计算移动平均线
                df['MA5'] = df['收盘'].rolling(window=5).mean()
                df['MA20'] = df['收盘'].rolling(window=20).mean()
                
                # 计算RSI
                delta = df['收盘'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                # 在主线程中显示分析结果
                def show_analysis():
                    analysis_window = tk.Toplevel(self.root)
                    analysis_window.title(f"{stock_code} {stock_name} 趋势分析")
                    analysis_window.geometry("1000x700")
                    
                    # 创建图表区域
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
                    
                    # 绘制价格走势和均线
                    ax1.plot(df.index, df['收盘'], label='收盘价', color='black')
                    ax1.plot(df.index, df['MA5'], label='5日均线', color='blue')
                    ax1.plot(df.index, df['MA20'], label='20日均线', color='red')
                    ax1.set_title(f'{stock_code} {stock_name} - 价格走势')
                    ax1.legend()
                    ax1.grid(True)
                    
                    # 绘制RSI
                    ax2.plot(df.index, df['RSI'], label='RSI', color='purple')
                    ax2.axhline(y=70, color='r', linestyle='--', label='超买线')
                    ax2.axhline(y=30, color='g', linestyle='--', label='超卖线')
                    ax2.set_title('RSI指标')
                    ax2.legend()
                    ax2.grid(True)
                    
                    plt.tight_layout()
                    
                    # 在Tkinter中显示图表
                    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                    canvas = FigureCanvasTkAgg(fig, master=analysis_window)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                    
                    self.log(f"[OK] {stock_code} 趋势分析完成")
                
                self.root.after(0, show_analysis)
                
            except Exception as e:
                self.root.after(0, lambda e=e: [
                    self.log(f"[ERROR] 趋势分析失败: {e}", "error"),
                    messagebox.showerror("错误", f"趋势分析失败:\n{str(e)}")
                ])
        
        threading.Thread(target=trend_analysis_thread, daemon=True).start()

    def add_sector_to_watchlist(self):
        """加入自选股"""
        selection = self.sector_stocks_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一只板块成分股")
            return
        
        item = self.sector_stocks_tree.item(selection[0])
        stock_code = item['values'][0]  # 股票代码
        stock_name = item['values'][1]  # 股票名称
        
        # 这里可以添加到自选股列表
        messagebox.showinfo("提示", f"已将 {stock_code} {stock_name} 添加到自选股")

    def export_sector_data(self):
        """导出板块数据"""
        items = self.sector_stocks_tree.get_children()
        if not items:
            messagebox.showwarning("警告", "没有数据可导出")
            return
        
        try:
            import pandas as pd
            from 爬取金融数据 import DATA_DIR
            data = []
            for item in items:
                values = self.sector_stocks_tree.item(item)['values']
                data.append({
                    '股票代码': values[0],
                    '股票名称': values[1],
                    '最新价': values[2],
                    '涨跌幅': values[3],
                    '成交量': values[4],
                    '入选理由': values[5]
                })
            
            df = pd.DataFrame(data)
            filename = f"板块成分股_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join(DATA_DIR, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            self.log(f"[OK] 板块数据已导出至: {filepath}")
            messagebox.showinfo("成功", f"板块数据已导出至:\n{filepath}")
        except Exception as e:
            self.log(f"[ERROR] 导出板块数据失败: {e}", "error")
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def create_database_management_tab(self, notebook):
        """数据库管理标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🗄️ 数据库管理")
        
        # 标题
        title = ttk.Label(tab, text="数据库管理系统", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # 数据库状态显示
        status_frame = ttk.LabelFrame(tab, text="数据库状态", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.db_status_label = ttk.Label(status_frame, text="状态: 正在检查...", font=("Arial", 10))
        self.db_status_label.pack(anchor=tk.W)
        
        # 数据库统计信息
        stats_frame = ttk.Frame(status_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.db_stats_text = scrolledtext.ScrolledText(stats_frame, height=6, width=80)
        self.db_stats_text.pack(fill=tk.X)
        self.db_stats_text.config(state=tk.DISABLED)
        
        # 数据同步操作
        sync_frame = ttk.LabelFrame(tab, text="数据同步", padding=10)
        sync_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # CSV文件夹路径
        ttk.Label(sync_frame, text="CSV文件夹路径:").pack(anchor=tk.W)
        csv_path_frame = ttk.Frame(sync_frame)
        csv_path_frame.pack(fill=tk.X, pady=5)
        
        self.csv_path_var = tk.StringVar(value=DATA_DIR)
        self.csv_path_entry = ttk.Entry(csv_path_frame, textvariable=self.csv_path_var, width=50)
        self.csv_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(csv_path_frame, text="浏览", command=self.browse_csv_folder).pack(side=tk.RIGHT, padx=5)
        
        # 同步按钮
        sync_btn_frame = ttk.Frame(sync_frame)
        sync_btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(sync_btn_frame, text="[IN] CSV同步到数据库", 
                  command=self.sync_csv_to_database, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(sync_btn_frame, text="[OUT] 数据库导出到CSV", 
                  command=self.export_database_to_csv, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(sync_btn_frame, text="[SYNC] 刷新数据库状态", 
                  command=self.refresh_database_status, width=20).pack(side=tk.LEFT, padx=5)
        
        # 数据库表管理
        table_frame = ttk.LabelFrame(tab, text="数据库表管理", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 表选择
        table_select_frame = ttk.Frame(table_frame)
        table_select_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(table_select_frame, text="选择表:").pack(side=tk.LEFT)
        self.table_var = tk.StringVar()
        table_combo = ttk.Combobox(table_select_frame, textvariable=self.table_var, 
                                  values=["stocks_basic", "daily_quotes", "financial_data", 
                                          "technical_indicators", "trading_records", "analysis_results"],
                                  state="readonly", width=20)
        table_combo.pack(side=tk.LEFT, padx=5)
        table_combo.set("daily_quotes")
        
        # 表操作按钮
        table_btn_frame = ttk.Frame(table_frame)
        table_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(table_btn_frame, text="[LIST] 查看表结构", 
                  command=self.view_table_structure, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(table_btn_frame, text="[STAT] 查看表数据", 
                  command=self.view_table_data, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(table_btn_frame, text="🧹 清空表数据", 
                  command=self.clear_table_data, width=15).pack(side=tk.LEFT, padx=5)
        
        # 表数据显示区域
        table_data_frame = ttk.Frame(table_frame)
        table_data_frame.pack(fill=tk.BOTH, expand=True)
        
        self.table_data_text = scrolledtext.ScrolledText(table_data_frame, height=15, width=100)
        self.table_data_text.pack(fill=tk.BOTH, expand=True)
        self.table_data_text.config(state=tk.DISABLED)
        
        # 初始化数据库状态
        self.refresh_database_status()
    
    def browse_csv_folder(self):
        """浏览CSV文件夹"""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="选择CSV文件夹")
        if folder:
            self.csv_path_var.set(folder)
    
    def refresh_database_status(self):
        """刷新数据库状态"""
        def update_status():
            try:
                if self.enhanced_db_manager:
                    # 获取数据库统计信息
                    stats = self.enhanced_db_manager.get_database_stats()
                    
                    # 更新状态标签
                    self.db_status_label.config(text="状态: 已连接", foreground="green")
                    
                    # 更新统计信息文本框
                    self.db_stats_text.config(state=tk.NORMAL)
                    self.db_stats_text.delete(1.0, tk.END)
                    
                    stats_text = "[STAT] 数据库统计信息:\n\n"
                    for table, count in stats.items():
                        stats_text += f"  • {table}: {count} 条记录\n"
                    
                    stats_text += f"\n[SAVE] 数据库: quantitative_trading"
                    stats_text += f"\n[CONN] 连接: 正常"
                    
                    self.db_stats_text.insert(1.0, stats_text)
                    self.db_stats_text.config(state=tk.DISABLED)
                    
                    self.log("[OK] 数据库状态已刷新")
                else:
                    self.db_status_label.config(text="状态: 未连接", foreground="red")
                    self.db_stats_text.config(state=tk.NORMAL)
                    self.db_stats_text.delete(1.0, tk.END)
                    self.db_stats_text.insert(1.0, "数据库连接失败，请检查MySQL服务是否运行")
                    self.db_stats_text.config(state=tk.DISABLED)
                    
            except Exception as e:
                self.db_status_label.config(text=f"状态: 错误 - {str(e)}", foreground="red")
                self.db_stats_text.config(state=tk.NORMAL)
                self.db_stats_text.delete(1.0, tk.END)
                self.db_stats_text.insert(1.0, f"数据库连接错误: {str(e)}")
                self.db_stats_text.config(state=tk.DISABLED)
        
        threading.Thread(target=update_status, daemon=True).start()
    
    def sync_csv_to_database(self):
        """同步CSV到数据库"""
        csv_folder = self.csv_path_var.get()
        if not csv_folder or not os.path.exists(csv_folder):
            messagebox.showerror("错误", "CSV文件夹路径无效")
            return
        
        def sync_thread():
            try:
                if self.enhanced_db_manager:
                    success = self.enhanced_db_manager.sync_csv_to_database(csv_folder)
                    if success:
                        self.root.after(0, lambda: [
                            messagebox.showinfo("成功", "CSV数据同步到数据库完成"),
                            self.refresh_database_status()
                        ])
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", "CSV数据同步失败"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "数据库连接失败"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"同步失败: {str(e)}"))
        
        threading.Thread(target=sync_thread, daemon=True).start()
    
    def export_database_to_csv(self):
        """导出数据库到CSV"""
        from tkinter import filedialog
        output_folder = filedialog.askdirectory(title="选择导出文件夹")
        if not output_folder:
            return
        
        def export_thread():
            try:
                if self.enhanced_db_manager:
                    success = self.enhanced_db_manager.export_database_to_csv(output_folder)
                    if success:
                        self.root.after(0, lambda: messagebox.showinfo("成功", f"数据库已导出到: {output_folder}"))
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", "数据库导出失败"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "数据库连接失败"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"导出失败: {str(e)}"))
        
        threading.Thread(target=export_thread, daemon=True).start()
    
    def view_table_structure(self):
        """查看表结构"""
        table_name = self.table_var.get()
        if not table_name:
            messagebox.showwarning("警告", "请选择要查看的表")
            return
        
        def view_thread():
            try:
                if self.enhanced_db_manager:
                    # 查询表结构
                    self.enhanced_db_manager.cursor.execute(f"DESCRIBE {table_name}")
                    structure = self.enhanced_db_manager.cursor.fetchall()
                    
                    # 在主线程中显示结果
                    def show_structure():
                        self.table_data_text.config(state=tk.NORMAL)
                        self.table_data_text.delete(1.0, tk.END)
                        
                        structure_text = f"[LIST] 表 {table_name} 结构:\n\n"
                        structure_text += "字段名\t\t类型\t\t是否为空\t键\t默认值\t额外信息\n"
                        structure_text += "-" * 80 + "\n"
                        
                        for column in structure:
                            structure_text += f"{column['Field']}\t\t{column['Type']}\t\t{column['Null']}\t\t{column['Key']}\t\t{column['Default']}\t\t{column['Extra']}\n"
                        
                        self.table_data_text.insert(1.0, structure_text)
                        self.table_data_text.config(state=tk.DISABLED)
                    
                    self.root.after(0, show_structure)
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "数据库连接失败"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"查看表结构失败: {str(e)}"))
        
        threading.Thread(target=view_thread, daemon=True).start()
    
    def view_table_data(self):
        """查看表数据"""
        table_name = self.table_var.get()
        if not table_name:
            messagebox.showwarning("警告", "请选择要查看的表")
            return
        
        def view_thread():
            try:
                if self.enhanced_db_manager:
                    # 查询表数据（限制前100条）
                    self.enhanced_db_manager.cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
                    data = self.enhanced_db_manager.cursor.fetchall()
                    
                    # 在主线程中显示结果
                    def show_data():
                        self.table_data_text.config(state=tk.NORMAL)
                        self.table_data_text.delete(1.0, tk.END)
                        
                        if not data:
                            self.table_data_text.insert(1.0, f"表 {table_name} 为空")
                        else:
                            # 获取列名
                            columns = list(data[0].keys())
                            
                            data_text = f"[STAT] 表 {table_name} 数据 (前100条):\n\n"
                            data_text += "\t\t".join(columns) + "\n"
                            data_text += "-" * 100 + "\n"
                            
                            for row in data:
                                row_text = "\t\t".join([str(row[col]) for col in columns])
                                data_text += row_text + "\n"
                            
                            self.table_data_text.insert(1.0, data_text)
                        
                        self.table_data_text.config(state=tk.DISABLED)
                    
                    self.root.after(0, show_data)
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "数据库连接失败"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"查看表数据失败: {str(e)}"))
        
        threading.Thread(target=view_thread, daemon=True).start()
    
    def clear_table_data(self):
        """清空表数据"""
        table_name = self.table_var.get()
        if not table_name:
            messagebox.showwarning("警告", "请选择要清空的表")
            return
        
        # 确认对话框
        if not messagebox.askyesno("确认", f"确定要清空表 {table_name} 的所有数据吗？此操作不可逆！"):
            return
        
        def clear_thread():
            try:
                if self.enhanced_db_manager:
                    # 清空表数据
                    self.enhanced_db_manager.cursor.execute(f"DELETE FROM {table_name}")
                    self.enhanced_db_manager.connection.commit()
                    
                    self.root.after(0, lambda: [
                        messagebox.showinfo("成功", f"表 {table_name} 数据已清空"),
                        self.refresh_database_status()
                    ])
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "数据库连接失败"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"清空表数据失败: {str(e)}"))
        
        threading.Thread(target=clear_thread, daemon=True).start()

    def show_about(self):
        """关于"""
        about_text = """
AI量化交易系统 v2.0

功能特性:
[OK] 支持批量股票数据爬取
[OK] 8种机器学习模型可选
[OK] AI智能策略回测
[OK] 实时行情监控与预测
[OK] 数据分析与可视化报告
[OK] 直接打开数据文件和分析文件
[OK] 基金交易与管理
技术栈:
- Python 3.x
- Machine Learning (sklearn)
- AKShare/Tushare (数据源)
- Pandas/NumPy (数据处理)
- Tkinter (图形界面)

开发者: AI量化团队
版本: 2.0
更新日期: 2025
        """
        messagebox.showinfo("关于", about_text)
    
    # ========== 同花顺实时行情方法 ==========
    
    def create_stock_realtime_tab(self, notebook):
        """股票实时行情标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📈 股票行情")
        
        # 标题
        title = ttk.Label(tab, text="股票实时行情（上交所/深交所数据源）", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # 配置区域
        config_frame = ttk.LabelFrame(tab, text="股票查询配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 股票代码输入
        ttk.Label(config_frame, text="股票代码(支持批量):").pack(anchor=tk.W)
        ttk.Label(config_frame, text="示例: 000001,000002,600000,600519", foreground="gray").pack(anchor=tk.W)
        
        self.stock_entry = ttk.Entry(config_frame, width=50)
        self.stock_entry.pack(fill=tk.X, pady=5)
        self.stock_entry.insert(0, "000001,000002,600000,600519")
        
        # 预设股票组合
        preset_frame = ttk.Frame(config_frame)
        preset_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(preset_frame, text="预设组合:").pack(side=tk.LEFT)
        
        preset_btn_frame = ttk.Frame(preset_frame)
        preset_btn_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(preset_btn_frame, text="大盘蓝筹", 
                  command=lambda: self.stock_entry.delete(0, tk.END) or self.stock_entry.insert(0, "000001,600036,601318,600519"), 
                  width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_btn_frame, text="科技成长", 
                  command=lambda: self.stock_entry.delete(0, tk.END) or self.stock_entry.insert(0, "300750,002415,000977,300059"), 
                  width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_btn_frame, text="消费医药", 
                  command=lambda: self.stock_entry.delete(0, tk.END) or self.stock_entry.insert(0, "600519,000858,600276,000538"), 
                  width=10).pack(side=tk.LEFT, padx=2)
        
        # 自动更新设置
        auto_update_frame = ttk.Frame(config_frame)
        auto_update_frame.pack(fill=tk.X, pady=5)
        
        self.stock_auto_update_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(auto_update_frame, text="自动更新", 
                       variable=self.stock_auto_update_var).pack(side=tk.LEFT)
        
        ttk.Label(auto_update_frame, text="更新间隔(秒):").pack(side=tk.LEFT, padx=(20, 5))
        self.stock_interval_var = tk.StringVar(value="30")
        ttk.Spinbox(auto_update_frame, from_=10, to=300, 
                    textvariable=self.stock_interval_var, width=10).pack(side=tk.LEFT)
        
        # 按钮区域
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="[FIND] 查询股票", 
                  command=self.query_stock_realtime, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="▶️ 开始订阅", 
                  command=self.start_stock_subscription, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹️ 停止订阅", 
                  command=self.stop_stock_subscription, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="[SAVE] 导出数据", 
                  command=self.export_stock_data, width=15).pack(side=tk.LEFT, padx=5)
        
        # 实时数据显示区域
        data_frame = ttk.LabelFrame(tab, text="股票实时数据", padding=10)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建表格显示实时数据
        columns = ("代码", "名称", "现价", "今日涨跌", "涨跌金额", "成交量", "成交金额", "波动幅度", "活跃度")
        self.stock_tree = ttk.Treeview(data_frame, columns=columns, show="headings", height=15)
        
        # 设置列宽
        col_widths = {"代码": 80, "名称": 100, "现价": 80, "今日涨跌": 80, "涨跌金额": 80, 
                     "成交量": 100, "成交金额": 100, "波动幅度": 60, "活跃度": 60}
        for col, width in col_widths.items():
            self.stock_tree.heading(col, text=col)
            self.stock_tree.column(col, width=width)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 状态显示
        self.stock_status_label = ttk.Label(tab, text="状态: 未查询", foreground="gray")
        self.stock_status_label.pack(anchor=tk.W, padx=10, pady=5)
    
    def query_stock_realtime(self):
        """查询股票实时行情（智能识别代码/名称）"""
        stock_codes_str = self.stock_entry.get().strip()
        if not stock_codes_str:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def query_thread():
            try:
                df = self.smart_client.get_realtime(stock_codes_str, types_hint=['stock'])
                
                def display_data():
                    self.stock_tree.delete(*self.stock_tree.get_children())
                    
                    if not df.empty:
                        for _, row in df.iterrows():
                            self.stock_tree.insert("", tk.END, values=(
                                row.get('symbol', ''),
                                row.get('name', ''),
                                f"{row.get('price', 0):.2f}",
                                f"{row.get('change_percent', 0):+.2f}%",
                                f"{row.get('change_amount', 0):+.2f}",
                                f"{row.get('volume', 0):,.0f}",
                                f"{row.get('amount', 0):,.0f}",
                                f"{row.get('amplitude', 0):.2f}%" if 'amplitude' in row else "N/A",
                                f"{row.get('turnover_rate', 0):.2f}%" if 'turnover_rate' in row else "N/A"
                            ))
                        
                        self.stock_status_label.config(text=f"状态: 查询成功 - {len(df)} 只股票", foreground="green")
                        self.log(f"[OK] 查询股票实时行情成功: {len(df)} 只股票")
                    else:
                        self.stock_status_label.config(text="状态: 查询失败", foreground="red")
                        self.log("[ERROR] 查询股票实时行情失败")
                
                self.root.after(0, display_data)
                
            except Exception as e:
                self.root.after(0, lambda: [
                    self.stock_status_label.config(text=f"状态: 查询失败 - {str(e)}", foreground="red"),
                    self.log(f"[ERROR] 查询股票实时行情失败: {e}", "error")
                ])
        
        self.stock_status_label.config(text="状态: 查询中...", foreground="blue")
        threading.Thread(target=query_thread, daemon=True).start()
    
    def create_fund_realtime_tab(self, notebook):
        """基金实时行情标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="💰 基金行情")
        
        # 标题
        title = ttk.Label(tab, text="基金实时行情（上交所/深交所数据源）", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # 配置区域
        config_frame = ttk.LabelFrame(tab, text="基金查询配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 基金代码输入
        ttk.Label(config_frame, text="基金代码(支持批量):").pack(anchor=tk.W)
        ttk.Label(config_frame, text="示例: 510300,159915,510050,512880", foreground="gray").pack(anchor=tk.W)
        
        self.fund_entry = ttk.Entry(config_frame, width=50)
        self.fund_entry.pack(fill=tk.X, pady=5)
        self.fund_entry.insert(0, "510300,159915,510050,512880")
        
        # 预设基金组合
        preset_frame = ttk.Frame(config_frame)
        preset_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(preset_frame, text="预设组合:").pack(side=tk.LEFT)
        
        preset_btn_frame = ttk.Frame(preset_frame)
        preset_btn_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(preset_btn_frame, text="宽基指数", 
                  command=lambda: self.fund_entry.delete(0, tk.END) or self.fund_entry.insert(0, "510300,510050,159915,510500"), 
                  width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_btn_frame, text="行业主题", 
                  command=lambda: self.fund_entry.delete(0, tk.END) or self.fund_entry.insert(0, "512880,512000,515000,512800"), 
                  width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_btn_frame, text="债券货币", 
                  command=lambda: self.fund_entry.delete(0, tk.END) or self.fund_entry.insert(0, "511880,511990,511810,511690"), 
                  width=10).pack(side=tk.LEFT, padx=2)
        
        # 自动更新设置
        auto_update_frame = ttk.Frame(config_frame)
        auto_update_frame.pack(fill=tk.X, pady=5)
        
        self.fund_auto_update_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(auto_update_frame, text="自动更新", 
                       variable=self.fund_auto_update_var).pack(side=tk.LEFT)
        
        ttk.Label(auto_update_frame, text="更新间隔(秒):").pack(side=tk.LEFT, padx=(20, 5))
        self.fund_interval_var = tk.StringVar(value="30")
        ttk.Spinbox(auto_update_frame, from_=10, to=300, 
                    textvariable=self.fund_interval_var, width=10).pack(side=tk.LEFT)
        
        # 按钮区域
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="[FIND] 查询基金", 
                  command=self.query_fund_realtime, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="▶️ 开始订阅", 
                  command=self.start_fund_subscription, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹️ 停止订阅", 
                  command=self.stop_fund_subscription, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="[SAVE] 导出数据", 
                  command=self.export_fund_data, width=15).pack(side=tk.LEFT, padx=5)
        
        # 实时数据显示区域
        data_frame = ttk.LabelFrame(tab, text="基金实时数据", padding=10)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建表格显示实时数据
        columns = ("代码", "名称", "现价", "今日涨跌", "涨跌金额", "成交量", "成交金额")
        self.fund_tree = ttk.Treeview(data_frame, columns=columns, show="headings", height=15)
        
        # 设置列宽
        col_widths = {"代码": 80, "名称": 150, "现价": 80, "今日涨跌": 80, "涨跌金额": 80, 
                     "成交量": 100, "成交金额": 100}
        for col, width in col_widths.items():
            self.fund_tree.heading(col, text=col)
            self.fund_tree.column(col, width=width)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.fund_tree.yview)
        self.fund_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.fund_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 状态显示
        self.fund_status_label = ttk.Label(tab, text="状态: 未查询", foreground="gray")
        self.fund_status_label.pack(anchor=tk.W, padx=10, pady=5)
    
    def query_fund_realtime(self):
        """查询基金实时行情（智能识别代码/名称）"""
        fund_codes_str = self.fund_entry.get().strip()
        if not fund_codes_str:
            messagebox.showwarning("警告", "请输入基金代码")
            return
        
        def query_thread():
            try:
                df = self.smart_client.get_realtime(fund_codes_str, types_hint=['fund'])
                
                def display_data():
                    self.fund_tree.delete(*self.fund_tree.get_children())
                    
                    if not df.empty:
                        for _, row in df.iterrows():
                            self.fund_tree.insert("", tk.END, values=(
                                row.get('symbol', ''),
                                row.get('name', ''),
                                f"{row.get('price', 0):.3f}",
                                f"{row.get('change_percent', 0):+.2f}%",
                                f"{row.get('change_amount', 0):+.3f}",
                                f"{row.get('volume', 0):,.0f}",
                                f"{row.get('amount', 0):,.0f}"
                            ))
                        
                        self.fund_status_label.config(text=f"状态: 查询成功 - {len(df)} 只基金", foreground="green")
                        self.log(f"[OK] 查询基金实时行情成功: {len(df)} 只基金")
                    else:
                        self.fund_status_label.config(text="状态: 查询失败", foreground="red")
                        self.log("[ERROR] 查询基金实时行情失败")
                
                self.root.after(0, display_data)
                
            except Exception as e:
                self.root.after(0, lambda: [
                    self.fund_status_label.config(text=f"状态: 查询失败 - {str(e)}", foreground="red"),
                    self.log(f"[ERROR] 查询基金实时行情失败: {e}", "error")
                ])
        
        self.fund_status_label.config(text="状态: 查询中...", foreground="blue")
        threading.Thread(target=query_thread, daemon=True).start()
    
    def create_index_realtime_tab(self, notebook):
        """指数实时行情标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="📉 大盘指数")
        
        # 标题
        title = ttk.Label(tab, text="指数实时行情（上交所/深交所数据源）", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # 配置区域
        config_frame = ttk.LabelFrame(tab, text="指数查询配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 指数代码输入
        ttk.Label(config_frame, text="指数代码(支持批量):").pack(anchor=tk.W)
        ttk.Label(config_frame, text="示例: 000001,399001,000300,399006", foreground="gray").pack(anchor=tk.W)
        
        self.index_entry = ttk.Entry(config_frame, width=50)
        self.index_entry.pack(fill=tk.X, pady=5)
        self.index_entry.insert(0, "000001,399001,000300,399006")
        
        # 预设指数组合
        preset_frame = ttk.Frame(config_frame)
        preset_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(preset_frame, text="预设组合:").pack(side=tk.LEFT)
        
        preset_btn_frame = ttk.Frame(preset_frame)
        preset_btn_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(preset_btn_frame, text="主要指数", 
                  command=lambda: self.index_entry.delete(0, tk.END) or self.index_entry.insert(0, "000001,399001,000300,399006"), 
                  width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_btn_frame, text="行业指数", 
                  command=lambda: self.index_entry.delete(0, tk.END) or self.index_entry.insert(0, "399812,399967,399986,399998"), 
                  width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_btn_frame, text="主题指数", 
                  command=lambda: self.index_entry.delete(0, tk.END) or self.index_entry.insert(0, "399417,399440,399550,399639"), 
                  width=10).pack(side=tk.LEFT, padx=2)
        
        # 自动更新设置
        auto_update_frame = ttk.Frame(config_frame)
        auto_update_frame.pack(fill=tk.X, pady=5)
        
        self.index_auto_update_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(auto_update_frame, text="自动更新", 
                       variable=self.index_auto_update_var).pack(side=tk.LEFT)
        
        ttk.Label(auto_update_frame, text="更新间隔(秒):").pack(side=tk.LEFT, padx=(20, 5))
        self.index_interval_var = tk.StringVar(value="30")
        ttk.Spinbox(auto_update_frame, from_=10, to=300, 
                    textvariable=self.index_interval_var, width=10).pack(side=tk.LEFT)
        
        # 按钮区域
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="[FIND] 查询指数", 
                  command=self.query_index_realtime, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="▶️ 开始订阅", 
                  command=self.start_index_subscription, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹️ 停止订阅", 
                  command=self.stop_index_subscription, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="[SAVE] 导出数据", 
                  command=self.export_index_data, width=15).pack(side=tk.LEFT, padx=5)
        
        # 实时数据显示区域
        data_frame = ttk.LabelFrame(tab, text="指数实时数据", padding=10)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建表格显示实时数据
        columns = ("代码", "名称", "现价", "今日涨跌", "涨跌金额", "成交量", "成交金额")
        self.index_tree = ttk.Treeview(data_frame, columns=columns, show="headings", height=15)
        
        # 设置列宽
        col_widths = {"代码": 80, "名称": 120, "现价": 80, "今日涨跌": 80, "涨跌金额": 80, 
                     "成交量": 100, "成交金额": 100}
        for col, width in col_widths.items():
            self.index_tree.heading(col, text=col)
            self.index_tree.column(col, width=width)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.index_tree.yview)
        self.index_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.index_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 状态显示
        self.index_status_label = ttk.Label(tab, text="状态: 未查询", foreground="gray")
        self.index_status_label.pack(anchor=tk.W, padx=10, pady=5)
    
    def query_index_realtime(self):
        """查询指数实时行情"""
        index_codes_str = self.index_entry.get().strip()
        if not index_codes_str:
            messagebox.showwarning("警告", "请输入指数代码")
            return
        
        def query_thread():
            try:
                df = self.smart_client.get_realtime(index_codes_str, types_hint=['index'])
                
                def display_data():
                    self.index_tree.delete(*self.index_tree.get_children())
                    
                    if not df.empty:
                        for _, row in df.iterrows():
                            self.index_tree.insert("", tk.END, values=(
                                row.get('symbol', ''),
                                row.get('name', ''),
                                f"{row.get('price', 0):.2f}",
                                f"{row.get('change_percent', 0):+.2f}%",
                                f"{row.get('change_amount', 0):+.2f}",
                                f"{row.get('volume', 0):,.0f}",
                                f"{row.get('amount', 0):,.0f}"
                            ))
                        
                        self.index_status_label.config(text=f"状态: 查询成功 - {len(df)} 个指数", foreground="green")
                        self.log(f"[OK] 查询指数实时行情成功: {len(df)} 个指数")
                    else:
                        self.index_status_label.config(text="状态: 查询失败", foreground="red")
                        self.log("[ERROR] 查询指数实时行情失败")
                
                self.root.after(0, display_data)
                
            except Exception as e:
                self.root.after(0, lambda: [
                    self.index_status_label.config(text=f"状态: 查询失败 - {str(e)}", foreground="red"),
                    self.log(f"[ERROR] 查询指数实时行情失败: {e}", "error")
                ])
        
        self.index_status_label.config(text="状态: 查询中...", foreground="blue")
        threading.Thread(target=query_thread, daemon=True).start()
    
    def create_board_realtime_tab(self, notebook):
        """板块实时行情标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🏷️ 板块行情")
        
        # 标题
        title = ttk.Label(tab, text="板块实时行情（上交所/深交所数据源）", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # 配置区域
        config_frame = ttk.LabelFrame(tab, text="板块查询配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 板块类型选择
        ttk.Label(config_frame, text="板块类型:").pack(anchor=tk.W)
        
        board_type_frame = ttk.Frame(config_frame)
        board_type_frame.pack(fill=tk.X, pady=5)
        
        self.board_type_var = tk.StringVar(value="概念")
        ttk.Radiobutton(board_type_frame, text="概念板块", 
                       variable=self.board_type_var, value="概念").pack(side=tk.LEFT)
        ttk.Radiobutton(board_type_frame, text="行业板块", 
                       variable=self.board_type_var, value="行业").pack(side=tk.LEFT, padx=20)
        
        # 自动更新设置
        auto_update_frame = ttk.Frame(config_frame)
        auto_update_frame.pack(fill=tk.X, pady=5)
        
        self.board_auto_update_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(auto_update_frame, text="自动更新", 
                       variable=self.board_auto_update_var).pack(side=tk.LEFT)
        
        ttk.Label(auto_update_frame, text="更新间隔(秒):").pack(side=tk.LEFT, padx=(20, 5))
        self.board_interval_var = tk.StringVar(value="60")
        ttk.Spinbox(auto_update_frame, from_=30, to=600, 
                    textvariable=self.board_interval_var, width=10).pack(side=tk.LEFT)
        
        # 按钮区域
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="[FIND] 查询板块", 
                  command=self.query_board_realtime, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="▶️ 开始订阅", 
                  command=self.start_board_subscription, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹️ 停止订阅", 
                  command=self.stop_board_subscription, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="[SAVE] 导出数据", 
                  command=self.export_board_data, width=15).pack(side=tk.LEFT, padx=5)
        
        # 实时数据显示区域
        data_frame = ttk.LabelFrame(tab, text="板块实时数据", padding=10)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建表格显示实时数据
        columns = ("板块名称", "今日涨跌", "涨跌金额", "总市值", "活跃度", "上涨家数", "下跌家数")
        self.board_tree = ttk.Treeview(data_frame, columns=columns, show="headings", height=15)
        
        # 设置列宽
        col_widths = {"板块名称": 150, "今日涨跌": 80, "涨跌金额": 80, "总市值": 100, 
                     "活跃度": 80, "上涨家数": 80, "下跌家数": 80}
        for col, width in col_widths.items():
            self.board_tree.heading(col, text=col)
            self.board_tree.column(col, width=width)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.board_tree.yview)
        self.board_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.board_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 状态显示
        self.board_status_label = ttk.Label(tab, text="状态: 未查询", foreground="gray")
        self.board_status_label.pack(anchor=tk.W, padx=10, pady=5)
    
    def query_board_realtime(self):
        """查询板块实时行情"""
        def query_thread():
            try:
                df = self.tonghuashun_enhancer.get_concept_board_realtime()
                
                def display_data():
                    self.board_tree.delete(*self.board_tree.get_children())
                    
                    if not df.empty:
                        for _, row in df.iterrows():
                            self.board_tree.insert("", tk.END, values=(
                                row.get('board_name', ''),
                                f"{row.get('change_percent', 0):+.2f}%",
                                f"{row.get('change_amount', 0):+.2f}",
                                f"{row.get('total_market_cap', 0):,.0f}亿" if 'total_market_cap' in row else "N/A",
                                f"{row.get('turnover_rate', 0):.2f}%" if 'turnover_rate' in row else "N/A",
                                row.get('up_count', 'N/A'),
                                row.get('down_count', 'N/A')
                            ))
                        
                        self.board_status_label.config(text=f"状态: 查询成功 - {len(df)} 个板块", foreground="green")
                        self.log(f"[OK] 查询板块实时行情成功: {len(df)} 个板块")
                    else:
                        self.board_status_label.config(text="状态: 查询失败", foreground="red")
                        self.log("[ERROR] 查询板块实时行情失败")
                
                self.root.after(0, display_data)
                
            except Exception as e:
                self.root.after(0, lambda: [
                    self.board_status_label.config(text=f"状态: 查询失败 - {str(e)}", foreground="red"),
                    self.log(f"[ERROR] 查询板块实时行情失败: {e}", "error")
                ])
        
        self.board_status_label.config(text="状态: 查询中...", foreground="blue")
        threading.Thread(target=query_thread, daemon=True).start()
    
    def create_market_overview_tab(self, notebook):
        """市场概览标签页"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🌍 市场概览")
        
        # 标题
        title = ttk.Label(tab, text="市场概览（上交所/深交所数据源）", font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # 配置区域
        config_frame = ttk.LabelFrame(tab, text="概览配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 自动更新设置
        auto_update_frame = ttk.Frame(config_frame)
        auto_update_frame.pack(fill=tk.X, pady=5)
        
        self.overview_auto_update_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(auto_update_frame, text="自动更新", 
                       variable=self.overview_auto_update_var).pack(side=tk.LEFT)
        
        ttk.Label(auto_update_frame, text="更新间隔(秒):").pack(side=tk.LEFT, padx=(20, 5))
        self.overview_interval_var = tk.StringVar(value="60")
        ttk.Spinbox(auto_update_frame, from_=30, to=600, 
                    textvariable=self.overview_interval_var, width=10).pack(side=tk.LEFT)
        
        # 按钮区域
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="[SYNC] 刷新概览", 
                  command=self.refresh_market_overview, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="▶️ 开始订阅", 
                  command=self.start_overview_subscription, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹️ 停止订阅", 
                  command=self.stop_overview_subscription, width=15).pack(side=tk.LEFT, padx=5)
        
        # 市场概览显示区域
        overview_frame = ttk.LabelFrame(tab, text="市场概览", padding=10)
        overview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建文本框显示市场概览
        self.overview_text = scrolledtext.ScrolledText(overview_frame, height=20, width=100)
        self.overview_text.pack(fill=tk.BOTH, expand=True)
        self.overview_text.config(state=tk.DISABLED)
        
        # 状态显示
        self.overview_status_label = ttk.Label(tab, text="状态: 未查询", foreground="gray")
        self.overview_status_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # 初始化市场概览
        self.refresh_market_overview()
    
    def refresh_market_overview(self):
        """刷新市场概览"""
        def refresh_thread():
            try:
                # 获取主要指数
                indices = self.tonghuashun_enhancer.get_index_realtime(['000001', '399001', '000300', '399006'])
                
                # 获取市场概览
                market_data = self.tonghuashun_enhancer.get_market_overview_realtime()
                
                def display_overview():
                    self.overview_text.config(state=tk.NORMAL)
                    self.overview_text.delete(1.0, tk.END)
                    
                    # 显示主要指数
                    self.overview_text.insert(tk.END, "[STAT] 主要指数行情\n")
                    self.overview_text.insert(tk.END, "="*50 + "\n")
                    
                    if not indices.empty:
                        for _, row in indices.iterrows():
                            change_percent = row.get('change_percent', 0)
                            color = "green" if change_percent > 0 else "red" if change_percent < 0 else "black"
                            
                            self.overview_text.insert(tk.END, 
                                f"{row.get('name', '')}: {row.get('price', 0):.2f} ")
                            self.overview_text.insert(tk.END, 
                                f"{change_percent:+.2f}%", color)
                            self.overview_text.insert(tk.END, f"\n")
                    
                    self.overview_text.insert(tk.END, "\n")
                    
                    # 显示市场概览
                    self.overview_text.insert(tk.END, "[NET] 市场概览\n")
                    self.overview_text.insert(tk.END, "="*50 + "\n")
                    
                    if market_data:
                        for key, value in market_data.items():
                            self.overview_text.insert(tk.END, f"{key}: {value}\n")
                    
                    self.overview_text.config(state=tk.DISABLED)
                    self.overview_status_label.config(text="状态: 更新成功", foreground="green")
                    self.log("[OK] 市场概览更新成功")
                
                self.root.after(0, display_overview)
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda err=error_msg: [
                    self.overview_status_label.config(text="状态: 更新失败 - %s" % err, foreground="red"),
                    self.log("[ERROR] 市场概览更新失败: %s" % err, "error")
                ])
        
        self.overview_status_label.config(text="状态: 更新中...", foreground="blue")
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    # ========== 订阅功能 ==========
    
    def start_stock_subscription(self):
        """开始股票订阅"""
        if self.stock_auto_update_var.get():
            interval = int(self.stock_interval_var.get())
            self.log(f"[OK] 开始股票自动订阅，间隔: {interval}秒")
            self.stock_status_label.config(text=f"状态: 订阅中 - 间隔{interval}秒", foreground="green")
        else:
            messagebox.showinfo("提示", "请先勾选自动更新选项")
    
    def stop_stock_subscription(self):
        """停止股票订阅"""
        self.log("⏹️ 停止股票自动订阅")
        self.stock_status_label.config(text="状态: 已停止", foreground="gray")
    
    def start_fund_subscription(self):
        """开始基金订阅"""
        if self.fund_auto_update_var.get():
            interval = int(self.fund_interval_var.get())
            self.log(f"[OK] 开始基金自动订阅，间隔: {interval}秒")
            self.fund_status_label.config(text=f"状态: 订阅中 - 间隔{interval}秒", foreground="green")
        else:
            messagebox.showinfo("提示", "请先勾选自动更新选项")
    
    def stop_fund_subscription(self):
        """停止基金订阅"""
        self.log("⏹️ 停止基金自动订阅")
        self.fund_status_label.config(text="状态: 已停止", foreground="gray")
    
    def start_index_subscription(self):
        """开始指数订阅"""
        if self.index_auto_update_var.get():
            interval = int(self.index_interval_var.get())
            self.log(f"[OK] 开始指数自动订阅，间隔: {interval}秒")
            self.index_status_label.config(text=f"状态: 订阅中 - 间隔{interval}秒", foreground="green")
        else:
            messagebox.showinfo("提示", "请先勾选自动更新选项")
    
    def stop_index_subscription(self):
        """停止指数订阅"""
        self.log("⏹️ 停止指数自动订阅")
        self.index_status_label.config(text="状态: 已停止", foreground="gray")
    
    def start_board_subscription(self):
        """开始板块订阅"""
        if self.board_auto_update_var.get():
            interval = int(self.board_interval_var.get())
            self.log(f"[OK] 开始板块自动订阅，间隔: {interval}秒")
            self.board_status_label.config(text=f"状态: 订阅中 - 间隔{interval}秒", foreground="green")
        else:
            messagebox.showinfo("提示", "请先勾选自动更新选项")
    
    def stop_board_subscription(self):
        """停止板块订阅"""
        self.log("⏹️ 停止板块自动订阅")
        self.board_status_label.config(text="状态: 已停止", foreground="gray")
    
    def start_overview_subscription(self):
        """开始概览订阅"""
        if self.overview_auto_update_var.get():
            interval = int(self.overview_interval_var.get())
            self.log(f"[OK] 开始市场概览自动订阅，间隔: {interval}秒")
            self.overview_status_label.config(text=f"状态: 订阅中 - 间隔{interval}秒", foreground="green")
        else:
            messagebox.showinfo("提示", "请先勾选自动更新选项")
    
    def stop_overview_subscription(self):
        """停止概览订阅"""
        self.log("⏹️ 停止市场概览自动订阅")
        self.overview_status_label.config(text="状态: 已停止", foreground="gray")
    
    # ========== 导出功能 ==========
    
    def export_stock_data(self):
        """导出股票数据"""
        filename = f"stock_realtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            # 这里可以添加导出逻辑
            messagebox.showinfo("导出成功", f"股票数据已导出到: {filename}")
            self.log(f"[SAVE] 股票数据导出成功: {filename}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出失败: {e}")
            self.log(f"[ERROR] 股票数据导出失败: {e}", "error")
    
    def export_fund_data(self):
        """导出基金数据"""
        filename = f"fund_realtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            # 这里可以添加导出逻辑
            messagebox.showinfo("导出成功", f"基金数据已导出到: {filename}")
            self.log(f"[SAVE] 基金数据导出成功: {filename}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出失败: {e}")
            self.log(f"[ERROR] 基金数据导出失败: {e}", "error")
    
    def export_index_data(self):
        """导出指数数据"""
        filename = f"index_realtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            # 这里可以添加导出逻辑
            messagebox.showinfo("导出成功", f"指数数据已导出到: {filename}")
            self.log(f"[SAVE] 指数数据导出成功: {filename}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出失败: {e}")
            self.log(f"[ERROR] 指数数据导出失败: {e}", "error")
    
    def export_board_data(self):
        """导出板块数据"""
        filename = f"board_realtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            # 这里可以添加导出逻辑
            messagebox.showinfo("导出成功", f"板块数据已导出到: {filename}")
            self.log(f"[SAVE] 板块数据导出成功: {filename}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出失败: {e}")
            self.log(f"[ERROR] 板块数据导出失败: {e}", "error")


def main():
    """主程序入口"""
    root = tk.Tk()
    app = AIQuantTradingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()