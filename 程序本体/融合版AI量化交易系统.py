"""
融合版AI量化交易系统
将原有回测系统与实时交易API接口深度融合
支持：历史回测 + 实时交易 + 多模型AI + 风险管理
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
import json
from typing import Dict

# 尝试导入 customtkinter（现代化界面）
try:
    import customtkinter as ctk
    USE_CUSTOM_TK = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    USE_CUSTOM_TK = False
    print("提示: 安装 customtkinter 可获得更美观的界面 (pip install customtkinter)")

# 导入原有量化交易模块
try:
    from 爬取金融数据 import FinancialDataCrawler, clear_data_folder, DATA_DIR
    from 多模型AI量化交易 import (
        AI_MODELS, AITradingStrategy, MultiModelBacktester, 
        RealTimeMonitor, parse_stock_codes
    )
    from 分析数据 import FinancialDataAnalyzer
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保所有依赖文件在同一目录下")
    sys.exit(1)

# 导入实时交易API
from 实时交易API接口 import TradingAPI, MarketDataProvider, TradingAccount, RealTimeTradingEngine


class RedirectText:
    """重定向输出到文本框"""
    def __init__(self, text_widget, queue):
        self.text_widget = text_widget
        self.queue = queue
        
    def write(self, text):
        if text.strip():
            self.queue.put((text, None))
    
    def flush(self):
        pass


class EnhancedMultiModelBacktester:
    """增强版多模型回测器 - 融合实时交易功能"""
    
    def __init__(self, model_type='1', use_ai=True):
        # 初始化原有回测器
        self.backtester = MultiModelBacktester(model_type=model_type, use_ai=use_ai)
        
        # 初始化实时交易API
        self.trading_api = TradingAPI()
        self.realtime_account = None
        self.is_live_trading = False
        
        # 融合配置
        self.fusion_config = {
            'auto_switch_to_live': True,  # 回测成功后自动切换到实盘
            'min_backtest_performance': 0.05,  # 回测最低收益率要求
            'risk_management_enabled': True
        }
        
    def initialize_realtime_trading(self) -> bool:
        """初始化实时交易功能"""
        try:
            if self.trading_api.initialize():
                # 创建模拟交易账户
                self.realtime_account = self.trading_api.create_trading_account(
                    'fusion_account', 
                    initial_cash=1000000
                )
                
                # 注册AI策略到实时交易引擎
                self.trading_api.engine.register_strategy(
                    'ai_fusion_strategy', 
                    self._ai_realtime_strategy
                )
                
                print("[OK] 实时交易功能初始化成功")
                return True
            else:
                print("[ERROR] 实时交易功能初始化失败")
                return False
        except Exception as e:
            print(f"[ERROR] 实时交易初始化异常: {e}")
            return False
    
    def run_hybrid_backtest(self, stock_code, start_date=None, end_date=None, use_existing_data=False):
        """运行混合回测：历史回测 + 实时交易验证"""
        
        print(f"\n{'='*80}")
        print(f"[BOT] 混合回测模式启动 - 股票: {stock_code}")
        print(f"{'='*80}")
        
        # 第一阶段：历史回测
        print("\n[STAT] 阶段1: 历史数据回测...")
        
        if use_existing_data:
            backtest_result = self.backtester.run_backtest_with_existing_data(stock_code)
        else:
            backtest_result = self.backtester.run_backtest(stock_code, start_date, end_date)
        
        if not backtest_result:
            print("[ERROR] 历史回测失败，停止混合回测")
            return None
        
        # 第二阶段：实时交易验证（如果回测成功且满足条件）
        if (self.fusion_config['auto_switch_to_live'] and 
            backtest_result.get('total_return', 0) > self.fusion_config['min_backtest_performance']):
            
            print("\n[RUN] 阶段2: 启动实时交易验证...")
            
            # 订阅实时行情
            if self.trading_api.subscribe_market_data([stock_code]):
                # 开始实时交易
                self.trading_api.start_trading()
                self.is_live_trading = True
                
                print(f"[OK] 已启动 {stock_code} 的实时交易验证")
                print("[IDEA] 系统将在实时行情中验证策略效果")
                
                # 返回融合结果
                fusion_result = {
                    'backtest_result': backtest_result,
                    'live_trading_status': 'active',
                    'stock_code': stock_code,
                    'timestamp': datetime.now().isoformat()
                }
                
                return fusion_result
        
        return backtest_result
    
    def _ai_realtime_strategy(self, account: TradingAccount, market_data: Dict, engine: RealTimeTradingEngine):
        """AI实时交易策略"""
        
        # 使用原有AI策略的逻辑生成交易信号
        for symbol, data in market_data.items():
            # 这里可以集成原有AI策略的决策逻辑
            # 例如：使用训练好的模型预测买卖信号
            
            # 简单的示例策略：基于涨跌幅
            if data['change'] > 1.5 and symbol not in account.positions:
                # 买入信号
                quantity = int((account.cash * 0.2) / data['last_price'])  # 使用20%资金
                if quantity > 0:
                    order = account.place_order(symbol, 'buy', quantity)
                    print(f"[BOT] AI信号: 买入 {symbol} {quantity}股 (涨幅: {data['change']}%)")
                    
            elif data['change'] < -1.5 and symbol in account.positions:
                # 卖出信号
                position = account.positions[symbol]
                if position['quantity'] > 0:
                    order = account.place_order(symbol, 'sell', position['quantity'])
                    print(f"[BOT] AI信号: 卖出 {symbol} {position['quantity']}股 (跌幅: {data['change']}%)")
    
    def get_realtime_portfolio(self):
        """获取实时投资组合信息"""
        if self.realtime_account and self.trading_api:
            return self.trading_api.get_account_info('fusion_account')
        return None
    
    def stop_live_trading(self):
        """停止实时交易"""
        if self.is_live_trading:
            self.trading_api.stop_trading()
            self.is_live_trading = False
            print("🛑 实时交易已停止")


class FusionAITradingGUI:
    """融合版AI量化交易系统主界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("[BOT] AI量化交易系统 - 融合版 v3.0")
        self.root.geometry("1600x1000")
        
        # 设置图标
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 核心组件
        self.crawler = self._init_crawler()
        self.enhanced_backtester = None
        self.output_queue = queue.Queue()
        self.selected_data_file = None
        
        # 实时交易状态
        self.live_trading_active = False
        self.live_symbols = []
        
        # 创建界面
        self.create_menu()
        self.create_main_layout()
        
        # 配置样式
        self.configure_styles()
        
        # 启动输出更新
        self.update_output()
        
        # 欢迎信息
        self.log("="*80)
        self.log("[RUN] 欢迎使用 AI量化交易系统 - 融合版 v3.0")
        self.log("[IDEA] 支持: 历史回测 + 实时交易 + AI策略 + 风险管理")
        self.log("="*80)
        
        # 检查依赖
        self._check_dependencies()
    
    def _init_crawler(self):
        """初始化爬虫"""
        try:
            from 爬取金融数据 import FinancialDataCrawler
            return FinancialDataCrawler()
        except Exception as e:
            self.log(f"[ERROR] 爬虫初始化失败: {e}", "error")
            return None
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="清理数据", command=self.clear_data)
        tools_menu.add_command(label="检查依赖", command=self._check_dependencies)
        menubar.add_cascade(label="工具", menu=tools_menu)
        
        self.root.config(menu=menubar)
    
    def create_main_layout(self):
        """创建主界面布局"""
        
        # 使用 Notebook 实现标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 标签页1: 数据管理
        self.data_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.data_frame, text="[STAT] 数据管理")
        self.create_data_tab()
        
        # 标签页2: AI回测
        self.backtest_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.backtest_frame, text="[BOT] AI回测")
        self.create_backtest_tab()
        
        # 标签页3: 实时交易
        self.realtime_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.realtime_frame, text="[RUN] 实时交易")
        self.create_realtime_tab()
        
        # 标签页4: 监控面板
        self.monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.monitor_frame, text="[UP] 监控面板")
        self.create_monitor_tab()
        
        # 输出区域（所有标签页共享）
        self.create_output_area()
    
    def create_data_tab(self):
        """创建数据管理标签页"""
        # 数据爬取控件
        data_group = ttk.LabelFrame(self.data_frame, text="数据爬取", padding=10)
        data_group.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(data_group, text="股票代码:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.stock_entry = ttk.Entry(data_group, width=20)
        self.stock_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(data_group, text="开始日期:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.start_date_entry = ttk.Entry(data_group, width=15)
        self.start_date_entry.insert(0, "2023-01-01")
        self.start_date_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(data_group, text="结束日期:").grid(row=0, column=4, sticky='w', padx=5, pady=5)
        self.end_date_entry = ttk.Entry(data_group, width=15)
        self.end_date_entry.insert(0, "2024-12-31")
        self.end_date_entry.grid(row=0, column=5, padx=5, pady=5)
        
        self.fetch_btn = ttk.Button(data_group, text="爬取数据", command=self.fetch_data)
        self.fetch_btn.grid(row=0, column=6, padx=10, pady=5)
        
        # 数据管理按钮
        manage_group = ttk.Frame(data_group)
        manage_group.grid(row=1, column=0, columnspan=7, pady=10)
        
        ttk.Button(manage_group, text="分析数据", command=self.analyze_data).pack(side='left', padx=5)
        ttk.Button(manage_group, text="清理数据", command=self.clear_data).pack(side='left', padx=5)
        ttk.Button(manage_group, text="查看数据目录", command=self.show_data_dir).pack(side='left', padx=5)
    
    def create_backtest_tab(self):
        """创建AI回测标签页"""
        # 回测配置
        backtest_group = ttk.LabelFrame(self.backtest_frame, text="回测配置", padding=10)
        backtest_group.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(backtest_group, text="股票代码:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.backtest_stock_entry = ttk.Entry(backtest_group, width=20)
        self.backtest_stock_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 数据源选择
        self.data_source_var = tk.StringVar(value="download")
        ttk.Radiobutton(backtest_group, text="下载数据", variable=self.data_source_var, value="download").grid(row=1, column=0, sticky='w', padx=5)
        ttk.Radiobutton(backtest_group, text="现有数据", variable=self.data_source_var, value="existing").grid(row=1, column=1, sticky='w', padx=5)
        
        # 文件选择按钮
        self.select_file_btn = ttk.Button(backtest_group, text="选择数据文件", command=self.select_data_file)
        self.select_file_btn.grid(row=1, column=2, padx=10)
        
        # 时间范围（仅下载数据时显示）
        self.date_frame = ttk.Frame(backtest_group)
        self.date_frame.grid(row=2, column=0, columnspan=3, pady=5, sticky='w')
        
        ttk.Label(self.date_frame, text="开始日期:").pack(side='left', padx=5)
        self.backtest_start_date = ttk.Entry(self.date_frame, width=12)
        self.backtest_start_date.insert(0, "2023-01-01")
        self.backtest_start_date.pack(side='left', padx=5)
        
        ttk.Label(self.date_frame, text="结束日期:").pack(side='left', padx=5)
        self.backtest_end_date = ttk.Entry(self.date_frame, width=12)
        self.backtest_end_date.insert(0, "2024-12-31")
        self.backtest_end_date.pack(side='left', padx=5)
        
        # AI模型选择
        ttk.Label(backtest_group, text="AI模型:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.backtest_model_var = tk.StringVar(value="1")
        model_combo = ttk.Combobox(backtest_group, textvariable=self.backtest_model_var, 
                                  values=list(AI_MODELS.keys()), width=25)
        model_combo.grid(row=3, column=1, padx=5, pady=5)
        
        # 回测按钮
        self.backtest_btn = ttk.Button(backtest_group, text="开始混合回测", command=self.start_hybrid_backtest)
        self.backtest_btn.grid(row=3, column=2, padx=10, pady=5)
        
        # 结果显示区域
        self.result_text = scrolledtext.ScrolledText(backtest_group, height=15, width=80)
        self.result_text.grid(row=4, column=0, columnspan=3, pady=10, sticky='nsew')
    
    def create_realtime_tab(self):
        """创建实时交易标签页"""
        # 实时交易控制
        realtime_group = ttk.LabelFrame(self.realtime_frame, text="实时交易控制", padding=10)
        realtime_group.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(realtime_group, text="监控股票:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.live_symbols_entry = ttk.Entry(realtime_group, width=30)
        self.live_symbols_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 实时交易按钮
        btn_frame = ttk.Frame(realtime_group)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.init_realtime_btn = ttk.Button(btn_frame, text="初始化实时交易", command=self.initialize_realtime)
        self.init_realtime_btn.pack(side='left', padx=5)
        
        self.start_live_btn = ttk.Button(btn_frame, text="开始实时交易", command=self.start_live_trading)
        self.start_live_btn.pack(side='left', padx=5)
        
        self.stop_live_btn = ttk.Button(btn_frame, text="停止实时交易", command=self.stop_live_trading)
        self.stop_live_btn.pack(side='left', padx=5)
        
        # 持仓监控
        portfolio_group = ttk.LabelFrame(self.realtime_frame, text="持仓监控", padding=10)
        portfolio_group.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.portfolio_text = scrolledtext.ScrolledText(portfolio_group, height=12)
        self.portfolio_text.pack(fill='both', expand=True)
    
    def create_monitor_tab(self):
        """创建监控面板标签页"""
        # 系统状态监控
        status_group = ttk.LabelFrame(self.monitor_frame, text="系统状态", padding=10)
        status_group.pack(fill='x', padx=5, pady=5)
        
        self.status_text = scrolledtext.ScrolledText(status_group, height=8)
        self.status_text.pack(fill='both', expand=True)
        
        # 性能指标
        metrics_group = ttk.LabelFrame(self.monitor_frame, text="性能指标", padding=10)
        metrics_group.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.metrics_text = scrolledtext.ScrolledText(metrics_group, height=8)
        self.metrics_text.pack(fill='both', expand=True)
    
    def create_output_area(self):
        """创建输出区域"""
        output_frame = ttk.Frame(self.root)
        output_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(output_frame, text="系统输出:").pack(anchor='w')
        self.output_text = scrolledtext.ScrolledText(output_frame, height=12)
        self.output_text.pack(fill='x', pady=5)
    
    def configure_styles(self):
        """配置界面样式"""
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=5)
    
    def update_output(self):
        """更新输出区域"""
        try:
            while True:
                text, tag = self.output_queue.get_nowait()
                self.output_text.insert(tk.END, text)
                self.output_text.see(tk.END)
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_output)
    
    def log(self, message, tag=None):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.output_queue.put((log_message, tag))
    
    # ===================== 数据管理功能 =====================
    
    def fetch_data(self):
        """爬取数据"""
        stock_codes = self.stock_entry.get().strip()
        start_date = self.start_date_entry.get().strip()
        end_date = self.end_date_entry.get().strip()
        
        if not stock_codes:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def fetch_thread():
            try:
                self.log(f"开始爬取数据: {stock_codes}", "info")
                
                codes_list = parse_stock_codes(stock_codes)
                
                for code in codes_list:
                    self.log(f"正在爬取 {code} 的数据...")
                    success = self.crawler.crawl_stock_data(code, start_date, end_date)
                    if success:
                        self.log(f"[OK] {code} 数据爬取成功", "success")
                    else:
                        self.log(f"[ERROR] {code} 数据爬取失败", "error")
                
                self.log("数据爬取完成", "success")
                
            except Exception as e:
                self.log(f"[ERROR] 数据爬取异常: {e}", "error")
        
        threading.Thread(target=fetch_thread, daemon=True).start()
    
    def analyze_data(self):
        """分析数据"""
        stock_code = self.stock_entry.get().strip()
        
        if not stock_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def analyze_thread():
            try:
                analyzer = FinancialDataAnalyzer()
                analysis_result = analyzer.analyze_stock(stock_code)
                
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, analysis_result)
                
                self.log(f"[OK] {stock_code} 数据分析完成", "success")
                
            except Exception as e:
                self.log(f"[ERROR] 数据分析失败: {e}", "error")
        
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def clear_data(self):
        """清理数据"""
        if messagebox.askyesno("确认", "确定要清理所有数据吗？"):
            try:
                clear_data_folder()
                self.log("[OK] 数据清理完成", "success")
            except Exception as e:
                self.log(f"[ERROR] 数据清理失败: {e}", "error")
    
    def show_data_dir(self):
        """显示数据目录"""
        try:
            os.startfile(DATA_DIR)
            self.log(f"[FILE] 打开数据目录: {DATA_DIR}")
        except Exception as e:
            self.log(f"[ERROR] 打开目录失败: {e}", "error")
    
    # ===================== 回测功能 =====================
    
    def select_data_file(self):
        """选择数据文件"""
        try:
            import tkinter.filedialog as filedialog
            
            initial_dir = DATA_DIR if os.path.exists(DATA_DIR) else os.path.dirname(__file__)
            
            file_path = filedialog.askopenfilename(
                title="选择回测数据文件",
                initialdir=initial_dir,
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if file_path:
                filename = os.path.basename(file_path)
                stock_code = filename.split('_')[0]
                
                self.backtest_stock_entry.delete(0, tk.END)
                self.backtest_stock_entry.insert(0, stock_code)
                
                self.data_source_var.set("existing")
                self.selected_data_file = file_path
                
                self.log(f"[OK] 已选择数据文件: {filename}", "success")
                self.log(f"   股票代码: {stock_code}")
                self.log(f"   [OK] 文件已成功选定")
                
        except Exception as e:
            self.log(f"[ERROR] 选择文件失败: {e}", "error")
            messagebox.showerror("错误", f"选择文件失败: {e}")
    
    def start_hybrid_backtest(self):
        """开始混合回测"""
        stock_code = self.backtest_stock_entry.get().strip()
        model_type = self.backtest_model_var.get()
        data_source = self.data_source_var.get()
        
        if not stock_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def backtest_thread():
            try:
                # 初始化增强版回测器
                self.enhanced_backtester = EnhancedMultiModelBacktester(
                    model_type=model_type, 
                    use_ai=True
                )
                
                # 初始化实时交易功能
                if not self.enhanced_backtester.initialize_realtime_trading():
                    self.log("[WARN]  实时交易功能初始化失败，仅进行历史回测", "warning")
                
                # 重定向输出
                old_stdout = sys.stdout
                sys.stdout = RedirectText(self.output_text, self.output_queue)
                
                self.log("="*80)
                self.log(f"[BOT] 开始混合回测 - 股票: {stock_code}", "info")
                self.log(f"   模式: 历史回测 + 实时验证")
                self.log(f"   AI模型: {AI_MODELS.get(model_type, {}).get('name', '未知')}")
                self.log("="*80)
                
                # 执行混合回测
                if data_source == "download":
                    start_date = self.backtest_start_date.get().strip()
                    end_date = self.backtest_end_date.get().strip()
                    
                    if not start_date or not end_date:
                        messagebox.showwarning("警告", "请输入开始和结束日期")
                        return
                    
                    result = self.enhanced_backtester.run_hybrid_backtest(
                        stock_code, start_date, end_date
                    )
                else:
                    if hasattr(self, 'selected_data_file') and self.selected_data_file:
                        # 使用增强版回测器的指定文件功能
                        result = self.enhanced_backtester.backtester.run_backtest_with_specific_file(
                            stock_code, self.selected_data_file
                        )
                    else:
                        result = self.enhanced_backtester.run_hybrid_backtest(
                            stock_code, use_existing_data=True
                        )
                
                sys.stdout = old_stdout
                
                if result:
                    self.log("\n[OK] 混合回测完成！", "success")
                    
                    # 显示结果
                    self.result_text.delete(1.0, tk.END)
                    self.result_text.insert(tk.END, json.dumps(result, indent=2, ensure_ascii=False))
                
            except Exception as e:
                sys.stdout = old_stdout
                self.log(f"\n[ERROR] 混合回测失败: {e}", "error")
                messagebox.showerror("错误", f"混合回测失败: {e}")
        
        threading.Thread(target=backtest_thread, daemon=True).start()
    
    # ===================== 实时交易功能 =====================
    
    def initialize_realtime(self):
        """初始化实时交易"""
        if not self.enhanced_backtester:
            self.enhanced_backtester = EnhancedMultiModelBacktester()
        
        if self.enhanced_backtester.initialize_realtime_trading():
            self.log("[OK] 实时交易功能初始化成功", "success")
            self.live_trading_active = True
        else:
            self.log("[ERROR] 实时交易功能初始化失败", "error")
    
    def start_live_trading(self):
        """开始实时交易"""
        symbols = self.live_symbols_entry.get().strip()
        
        if not symbols:
            messagebox.showwarning("警告", "请输入要监控的股票代码")
            return
        
        if not self.enhanced_backtester or not hasattr(self.enhanced_backtester, 'trading_api'):
            messagebox.showwarning("警告", "请先初始化实时交易功能")
            return
        
        symbol_list = [s.strip() for s in symbols.split(',')]
        
        if self.enhanced_backtester.trading_api.subscribe_market_data(symbol_list):
            self.enhanced_backtester.trading_api.start_trading()
            self.live_trading_active = True
            self.live_symbols = symbol_list
            
            self.log(f"[RUN] 实时交易已启动 - 监控股票: {', '.join(symbol_list)}", "success")
            
            # 启动持仓监控更新
            self.update_portfolio_display()
        else:
            self.log("[ERROR] 实时交易启动失败", "error")
    
    def stop_live_trading(self):
        """停止实时交易"""
        if self.enhanced_backtester and hasattr(self.enhanced_backtester, 'stop_live_trading'):
            self.enhanced_backtester.stop_live_trading()
            self.live_trading_active = False
            self.log("🛑 实时交易已停止", "info")
    
    def update_portfolio_display(self):
        """更新持仓显示"""
        if self.live_trading_active and self.enhanced_backtester:
            portfolio = self.enhanced_backtester.get_realtime_portfolio()
            
            if portfolio:
                self.portfolio_text.delete(1.0, tk.END)
                self.portfolio_text.insert(tk.END, json.dumps(portfolio, indent=2, ensure_ascii=False))
            
            # 每秒更新一次
            self.root.after(1000, self.update_portfolio_display)
    
    def _check_dependencies(self):
        """检查依赖"""
        try:
            import akshare as ak
            self.log("[OK] akshare 依赖检查通过", "success")
        except ImportError:
            self.log("[WARN]  请安装 akshare: pip install akshare", "warning")
    
    def __del__(self):
        """析构函数 - 确保停止所有线程"""
        if hasattr(self, 'enhanced_backtester') and self.enhanced_backtester:
            self.enhanced_backtester.stop_live_trading()


def main():
    """主函数"""
    root = tk.Tk()
    
    if USE_CUSTOM_TK:
        app = FusionAITradingGUI(root)
    else:
        app = FusionAITradingGUI(root)
    
    root.mainloop()


if __name__ == "__main__":
    main()