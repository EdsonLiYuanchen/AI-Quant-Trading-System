"""
实时行情增强模块
增强东方财富数据源的实时更新功能
"""

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    ak = None
    HAS_AKSHARE = False
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import queue
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 智能数据查询模块（快路径：自动识别+直连东财+智能缓存）
try:
    from 智能数据查询 import SmartDataClient
    _SMART_CLIENT = SmartDataClient()
except Exception:
    _SMART_CLIENT = None


def _smart_quote(codes, type_hint):
    """优先走智能快路径（东财直连），失败返回 None"""
    if _SMART_CLIENT is None or not codes:
        return None
    try:
        df = _SMART_CLIENT.get_realtime(','.join([c for c in codes if c]), types_hint=type_hint, use_cache=True)
        return df if df is not None and not df.empty else None
    except Exception:
        return None


def _to_zh(df: pd.DataFrame) -> pd.DataFrame:
    """把智能快路径英文列转为中文列（保持该模块原有返回约定）"""
    if df is None or df.empty:
        return df
    out = pd.DataFrame({
        '代码': df.get('symbol', ''),
        '名称': df.get('name', ''),
        '最新价': df.get('price', 0.0),
        '涨跌幅': df.get('change_percent', 0.0),
        '涨跌额': df.get('change_amount', 0.0),
        '成交量': df.get('volume', 0),
        '成交额': df.get('amount', 0),
        '最高': df.get('high', 0.0),
        '最低': df.get('low', 0.0),
        '今开': df.get('open', 0.0),
        '昨收': df.get('pre_close', 0.0),
        '换手率': df.get('turnover_rate', 0.0),
    })
    return out


class RealtimeDataEnhancer:
    """实时数据增强器 - 东方财富数据源"""
    
    def __init__(self):
        self.cache = {}  # 数据缓存
        self.cache_timeout = 10  # 缓存超时(秒)
        self.update_queue = queue.Queue()  # 更新队列
        self.subscribers = {}  # 订阅者
        self.running = False
        self.update_thread = None
        
        # 配置网络重试策略
        self._setup_network_retry()
    
    def _setup_network_retry(self):
        """配置网络请求重试机制"""
        # 创建重试策略
        retry_strategy = Retry(
            total=3,  # 最多重试3次
            backoff_factor=1,  # 重试间隔：1, 2, 4秒
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
            allowed_methods=["GET", "POST"]
        )
        
        # 创建适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)
        
        # 配置session
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置超时时间
        self.timeout = 15
        
    def get_stock_realtime_batch(self, stock_codes: List[str] = None) -> pd.DataFrame:
        """
        获取股票实时行情（批量）
        :param stock_codes: 股票代码列表，None表示全部A股
        :return: DataFrame
        """
        # 智能快路径（有具体代码时）
        if stock_codes:
            smart_df = _smart_quote(stock_codes, ['stock'])
            if smart_df is not None:
                return _to_zh(smart_df)
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_spot_em()
                
                if stock_codes:
                    df = df[df['代码'].isin(stock_codes)]
                
                if df.empty:
                    if attempt < max_retries - 1:
                        print(f"[WARN] 股票数据为空，第{attempt+1}次重试...")
                        time.sleep(retry_delay)
                        continue
                
                return df
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 网络连接失败，第{attempt+1}次重试...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"[ERROR] 获取实时行情失败: 网络连接错误 ({e})")
                    return pd.DataFrame()
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 获取实时行情失败，第{attempt+1}次重试: {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[ERROR] 获取实时行情失败: {e}")
                    return pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_fund_realtime_batch(self, fund_codes: List[str] = None) -> pd.DataFrame:
        """
        获取基金实时行情（批量）
        :param fund_codes: 基金代码列表
        :return: DataFrame
        """
        # 智能快路径（有具体代码时）
        if fund_codes:
            smart_df = _smart_quote(fund_codes, ['fund'])
            if smart_df is not None:
                return _to_zh(smart_df)
        try:
            df = ak.fund_etf_spot_em()
            
            if fund_codes:
                df = df[df['代码'].isin(fund_codes)]
            
            return df
        except Exception as e:
            print(f"[ERROR] 获取基金实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_index_realtime(self, index_codes: List[str] = None) -> pd.DataFrame:
        """
        获取指数实时行情
        :param index_codes: 指数代码列表 ['000001', '399001']
        :return: DataFrame
        """
        # 智能快路径
        if index_codes:
            smart_df = _smart_quote(index_codes, ['index'])
            if smart_df is not None:
                return _to_zh(smart_df)
        try:
            # 获取主要指数
            df = ak.stock_zh_index_spot_em()
            
            if index_codes:
                df = df[df['代码'].isin(index_codes)]
            
            return df
        except Exception as e:
            print(f"[ERROR] 获取指数实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_board_realtime(self, board_name: str = None) -> pd.DataFrame:
        """
        获取板块实时行情
        :param board_name: 板块名称
        :return: DataFrame
        """
        try:
            if board_name:
                df = ak.stock_board_spot_em()
                df = df[df['板块名称'] == board_name]
            else:
                df = ak.stock_board_spot_em()
            
            return df
        except Exception as e:
            print(f"[ERROR] 获取板块实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_market_overview_realtime(self) -> Dict:
        """
        获取市场概览（实时）
        :return: dict
        """
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
            try:
                # 获取实时行情
                df = ak.stock_zh_a_spot_em()
                
                if df.empty:
                    if attempt < max_retries - 1:
                        print(f"[WARN] 市场数据为空，第{attempt+1}次重试...")
                        time.sleep(retry_delay)
                        continue
                    return {}
                
                overview = {
                    'update_time': datetime.now().strftime('%H:%M:%S'),
                    'total_stocks': len(df),
                    'up_count': len(df[df['涨跌幅'] > 0]),
                    'down_count': len(df[df['涨跌幅'] < 0]),
                    'flat_count': len(df[df['涨跌幅'] == 0]),
                    'limit_up': len(df[df['涨跌幅'] >= 9.9]),
                    'limit_down': len(df[df['涨跌幅'] <= -9.9]),
                    'turnover': df['成交额'].sum() / 1e8,  # 亿元
                    'shanghai_index': None,
                    'shenzhen_index': None
                }
                
                # 获取主要指数
                try:
                    index_df = ak.stock_zh_index_spot_em()
                    sh_index = index_df[index_df['代码'] == '000001']
                    if not sh_index.empty:
                        overview['shanghai_index'] = {
                            'code': '000001',
                            'name': '上证指数',
                            'price': sh_index.iloc[0]['最新价'],
                            'change': sh_index.iloc[0]['涨跌幅']
                        }
                    
                    sz_index = index_df[index_df['代码'] == '399001']
                    if not sz_index.empty:
                        overview['shenzhen_index'] = {
                            'code': '399001',
                            'name': '深证成指',
                            'price': sz_index.iloc[0]['最新价'],
                            'change': sz_index.iloc[0]['涨跌幅']
                        }
                except Exception as index_error:
                    print(f"[WARN] 获取指数数据失败: {index_error}")
                    # 指数数据失败不影响整体市场概览
                
                print("[OK] 市场概览数据获取成功")
                return overview
                
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 网络连接失败，第{attempt+1}次重试...")
                    time.sleep(retry_delay * (attempt + 1))  # 递增延迟
                    continue
                else:
                    print(f"[ERROR] 获取市场概览失败: 网络连接错误 ({e})")
                    return {}
                    
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 请求超时，第{attempt+1}次重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[ERROR] 获取市场概览失败: 请求超时 ({e})")
                    return {}
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 获取市场概览失败，第{attempt+1}次重试: {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[ERROR] 获取市场概览失败: {e}")
                    return {}
        
        return {}
    
    def get_stock_minute_realtime(self, stock_code: str) -> pd.DataFrame:
        """
        获取股票分时数据（实时）
        :param stock_code: 股票代码
        :return: DataFrame
        """
        try:
            df = ak.stock_zh_a_hist_min_em(symbol=stock_code, period='1')
            return df
        except Exception as e:
            print(f"[ERROR] 获取分时数据失败: {e}")
            return pd.DataFrame()
    
    def subscribe(self, callback, symbols: List[str] = None):
        """
        订阅实时数据更新
        :param callback: 回调函数
        :param symbols: 订阅的代码列表
        """
        subscriber_id = id(callback)
        self.subscribers[subscriber_id] = {
            'callback': callback,
            'symbols': symbols,
            'last_update': None
        }
        return subscriber_id
    
    def unsubscribe(self, subscriber_id):
        """取消订阅"""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
    
    def start_auto_update(self, interval: int = 30):
        """
        启动自动更新
        :param interval: 更新间隔(秒)
        """
        if self.running:
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, args=(interval,))
        self.update_thread.daemon = True
        self.update_thread.start()
        print(f"[OK] 自动更新已启动，间隔: {interval}秒")
    
    def stop_auto_update(self):
        """停止自动更新"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        print("⏹️  自动更新已停止")
    
    def _update_loop(self, interval: int):
        """更新循环"""
        while self.running:
            try:
                # 获取所有订阅者的代码
                all_symbols = set()
                for subscriber in self.subscribers.values():
                    if subscriber['symbols']:
                        all_symbols.update(subscriber['symbols'])
                
                # 区分股票和基金
                stock_symbols = [s for s in all_symbols if s[0].isdigit() and (s.startswith('0') or s.startswith('3') or s.startswith('6'))]
                fund_symbols = [s for s in all_symbols if s.startswith('5') or s.startswith('1')]
                
                # 获取实时数据
                stock_data = None
                fund_data = None
                
                if stock_symbols:
                    stock_data = self.get_stock_realtime_batch(stock_symbols)
                if fund_symbols:
                    fund_data = self.get_fund_realtime_batch(fund_symbols)
                
                # 通知订阅者
                for subscriber_id, subscriber in self.subscribers.items():
                    try:
                        # 根据订阅者的代码筛选数据
                        if subscriber['symbols']:
                            symbols_set = set(subscriber['symbols'])
                            
                            filtered_stock = stock_data[stock_data['代码'].isin(symbols_set)] if stock_data is not None else None
                            filtered_fund = fund_data[fund_data['代码'].isin(symbols_set)] if fund_data is not None else None
                            
                            subscriber['callback'](filtered_stock, filtered_fund, datetime.now())
                        else:
                            subscriber['callback'](stock_data, fund_data, datetime.now())
                    except Exception as e:
                        print(f"[ERROR] 通知订阅者失败: {e}")
                
            except Exception as e:
                print(f"[ERROR] 更新循环出错: {e}")
            
            # 等待下一次更新
            for _ in range(interval):
                if not self.running:
                    break
                time.sleep(1)


class RealtimeDisplay:
    """实时数据展示面板"""
    
    def __init__(self, enhancer: RealtimeDataEnhancer):
        self.enhancer = enhancer
        self.last_update = None
    
    def display_market_overview(self):
        """显示市场概览"""
        overview = self.enhancer.get_market_overview_realtime()
        
        if not overview:
            print("[ERROR] 无法获取市场概览")
            return
        
        print("\n" + "="*80)
        print(f"[STAT] 市场概览 - {overview.get('update_time', 'N/A')}")
        print("="*80)
        print(f"总股票数: {overview.get('total_stocks', 0)}")
        print(f"🟢 上涨: {overview.get('up_count', 0)}  |  🔴 下跌: {overview.get('down_count', 0)}  |  ⚪ 平盘: {overview.get('flat_count', 0)}")
        print(f"[UP] 涨停: {overview.get('limit_up', 0)}  |  [DOWN] 跌停: {overview.get('limit_down', 0)}")
        print(f"[MONEY] 总成交额: {overview.get('turnover', 0):.2f} 亿元")
        
        # 显示指数
        if overview.get('shanghai_index'):
            idx = overview['shanghai_index']
            change_color = "[UP]" if idx['change'] >= 0 else "[DOWN]"
            print(f"\n{change_color} {idx['name']}: {idx['price']:.2f} ({idx['change']:+.2f}%)")
        
        if overview.get('shenzhen_index'):
            idx = overview['shenzhen_index']
            change_color = "[UP]" if idx['change'] >= 0 else "[DOWN]"
            print(f"{change_color} {idx['name']}: {idx['price']:.2f} ({idx['change']:+.2f}%)")
        
        print("="*80)
    
    def display_stock_realtime(self, stock_codes: List[str] = None):
        """显示股票实时行情"""
        df = self.enhancer.get_stock_realtime_batch(stock_codes)
        
        if df.empty:
            print("[ERROR] 无法获取实时行情")
            return
        
        print("\n" + "="*100)
        print(f"[UP] 股票实时行情 - {datetime.now().strftime('%H:%M:%S')}")
        print("="*100)
        print(f"{'代码':<8} {'名称':<10} {'最新价':<10} {'涨跌幅':<10} {'涨跌额':<10} {'成交量':<12} {'成交额':<12}")
        print("-"*100)
        
        for _, row in df.iterrows():
            change_color = row['涨跌幅']
            change_str = f"{change_color:+.2f}%"
            
            print(f"{row['代码']:<8} {row['名称']:<10} {row['最新价']:<10.2f} {change_str:<10} "
                  f"{row['涨跌额']:+.2f}  {row['成交量']:>10,}  {row['成交额']:>10,.0f}")
        
        print("="*100)
    
    def display_fund_realtime(self, fund_codes: List[str] = None):
        """显示基金实时行情"""
        df = self.enhancer.get_fund_realtime_batch(fund_codes)
        
        if df.empty:
            print("[ERROR] 无法获取基金实时行情")
            return
        
        print("\n" + "="*100)
        print(f"[MONEY] 基金实时行情 - {datetime.now().strftime('%H:%M:%S')}")
        print("="*100)
        print(f"{'代码':<8} {'名称':<20} {'最新价':<10} {'涨跌幅':<10} {'成交量':<12} {'成交额':<12}")
        print("-"*100)
        
        for _, row in df.iterrows():
            change_color = row['涨跌幅']
            change_str = f"{change_color:+.2f}%"
            
            print(f"{row['代码']:<8} {row['名称']:<20} {row['最新价']:<10.2f} {change_str:<10} "
                  f"{row['成交量']:>10,}  {row['成交额']:>10,.0f}")
        
        print("="*100)


def test_realtime_data():
    """测试实时数据功能"""
    print("="*80)
    print("🧪 测试东方财富实时数据增强功能")
    print("="*80)
    
    enhancer = RealtimeDataEnhancer()
    display = RealtimeDisplay(enhancer)
    
    # 测试1: 市场概览
    print("\n【测试1】获取市场概览...")
    display.display_market_overview()
    
    # 测试2: 股票实时行情
    print("\n【测试2】获取股票实时行情...")
    test_stocks = ['000001', '000002', '600000', '600519']
    display.display_stock_realtime(test_stocks)
    
    # 测试3: 基金实时行情
    print("\n【测试3】获取基金实时行情...")
    test_funds = ['510300', '159915', '510050']
    display.display_fund_realtime(test_funds)
    
    # 测试4: 指数实时行情
    print("\n【测试4】获取指数实时行情...")
    index_df = enhancer.get_index_realtime(['000001', '399001'])
    if not index_df.empty:
        print("\n指数实时行情:")
        print(index_df.to_string(index=False))
    
    # 测试5: 订阅功能
    print("\n【测试5】测试订阅功能...")
    
    def callback(stock_data, fund_data, timestamp):
        print(f"\n[CLOCK] 数据更新时间: {timestamp.strftime('%H:%M:%S')}")
        if stock_data is not None and not stock_data.empty:
            print(f"   更新了 {len(stock_data)} 只股票")
        if fund_data is not None and not fund_data.empty:
            print(f"   更新了 {len(fund_data)} 只基金")
    
    subscriber_id = enhancer.subscribe(callback, ['000001', '510300'])
    print(f"[OK] 已订阅，订阅ID: {subscriber_id}")
    
    # 启动自动更新
    enhancer.start_auto_update(interval=10)
    
    print("\n⏳ 运行30秒自动更新...")
    time.sleep(30)
    
    # 停止自动更新
    enhancer.stop_auto_update()
    enhancer.unsubscribe(subscriber_id)
    
    print("\n[OK] 测试完成！")


if __name__ == "__main__":
    test_realtime_data()
