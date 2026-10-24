"""
同花顺实时行情增强器
使用同花顺数据源替代东方财富，提供更稳定的实时数据
支持代理IP、数据缓存、限流自动检测
"""

import os
import numpy as np
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
import json
import hashlib

# 默认配置
DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data_cache')
DEFAULT_CACHE_TTL = 300  # 缓存有效期（秒）
DEFAULT_PROXY = None  # 默认不使用代理

# 智能数据查询模块（快路径：自动识别+直连东财+智能缓存）
try:
    from 智能数据查询 import SmartDataClient
    _SMART_CLIENT = SmartDataClient()
except Exception:
    _SMART_CLIENT = None


def _smart_quote(codes, type_hint):
    """优先走智能快路径（直连东财，毫秒级），失败返回 None"""
    if _SMART_CLIENT is None or not codes:
        return None
    try:
        text = ','.join([c for c in codes if c])
        df = _SMART_CLIENT.get_realtime(text, types_hint=type_hint, use_cache=True)
        return df if df is not None and not df.empty else None
    except Exception:
        return None


class TonghuashunRealtimeEnhancer:
    """同花顺实时数据增强器"""
    
    def __init__(self, proxy: str = None, cache_dir: str = DEFAULT_CACHE_DIR, cache_ttl: int = DEFAULT_CACHE_TTL):
        # 代理配置
        self.proxy = proxy
        self.proxy_enabled = proxy is not None
        
        # 缓存配置
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.memory_cache = {}  # 内存缓存
        self._init_cache_dir()
        
        # 限流检测
        self.rate_limit_detected = False
        self.rate_limit_time = 0
        self.rate_limit_cooldown = 300  # 限流冷却时间(秒)
        
        # 其他属性
        self.update_queue = queue.Queue()  # 更新队列
        self.subscribers = {}  # 订阅者
        self.running = False
        self.update_thread = None
        
        # 配置网络重试策略
        self._setup_network_retry()
        
        print("[INFO] 初始化完成 - 代理: %s, 缓存目录: %s" % ('已启用' if self.proxy_enabled else '未启用', cache_dir))
    
    def _init_cache_dir(self):
        """初始化缓存目录"""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def set_proxy(self, proxy: str):
        """设置代理服务器"""
        self.proxy = proxy
        self.proxy_enabled = proxy is not None
        if self.proxy_enabled:
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }
            print(f"[CONN] 已设置代理: {proxy}")
        else:
            self.session.proxies = {}
            print("[CONN] 已禁用代理")
    
    def _get_cache_key(self, data_type: str, params: tuple = ()) -> str:
        """生成缓存键"""
        key_str = f"{data_type}_{params}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _load_cache(self, data_type: str, params: tuple = ()) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        # 先检查内存缓存
        cache_key = self._get_cache_key(data_type, params)
        if cache_key in self.memory_cache:
            timestamp, df = self.memory_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                print(f"📡 命中内存缓存: {data_type}")
                return df
        
        # 再检查文件缓存
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            file_mtime = os.path.getmtime(cache_file)
            if time.time() - file_mtime < self.cache_ttl:
                try:
                    df = pd.read_pickle(cache_file)
                    # 更新内存缓存
                    self.memory_cache[cache_key] = (time.time(), df)
                    print(f"📡 命中文件缓存: {data_type}")
                    return df
                except:
                    pass
        
        return None
    
    def _save_cache(self, data_type: str, params: tuple, df: pd.DataFrame):
        """保存数据到缓存"""
        cache_key = self._get_cache_key(data_type, params)
        
        # 保存到内存缓存
        self.memory_cache[cache_key] = (time.time(), df)
        
        # 保存到文件缓存
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        try:
            df.to_pickle(cache_file)
        except Exception as e:
            print(f"[WARN] 缓存保存失败: {e}")
    
    def _check_rate_limit(self) -> bool:
        """检查是否被限流"""
        if self.rate_limit_detected:
            if time.time() - self.rate_limit_time < self.rate_limit_cooldown:
                remaining = self.rate_limit_cooldown - (time.time() - self.rate_limit_time)
                print(f"⏳ 限流冷却中，剩余 {int(remaining)} 秒")
                return True
            else:
                # 限流冷却时间已过，重置状态
                self.rate_limit_detected = False
                print("[OK] 限流冷却时间已过，尝试重新连接")
        return False
    
    def _detect_rate_limit(self, error_msg: str):
        """检测限流（需要连续多次失败才判定为限流）"""
        # 增加连续失败计数器
        if not hasattr(self, 'consecutive_failures'):
            self.consecutive_failures = 0
        
        if 'RemoteDisconnected' in error_msg or 'Connection aborted' in error_msg:
            self.consecutive_failures += 1
            print(f"[WARN] 连接失败 {self.consecutive_failures} 次")
            
            # 连续失败5次以上才判定为限流（提高阈值减少误判）
            if self.consecutive_failures >= 5:
                self.rate_limit_detected = True
                self.rate_limit_time = time.time()
                self.rate_limit_cooldown = 60  # 缩短冷却时间为1分钟
                self.consecutive_failures = 0  # 重置计数器
                print("[WARN] 检测到服务器限流，进入冷却模式（1分钟）")
        else:
            # 成功或其他错误，重置计数器
            self.consecutive_failures = 0
    
    def _setup_network_retry(self):
        """配置网络请求重试机制"""
        # 创建重试策略
        retry_strategy = Retry(
            total=5,  # 增加重试次数
            backoff_factor=2,  # 重试间隔：2, 4, 8, 16秒
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
            allowed_methods=["GET", "POST"]
        )
        
        # 创建适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)
        
        # 配置session
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置更长的超时时间
        self.timeout = 30
        
        # 添加请求头，模拟真实浏览器
        # 轮换多个User-Agent避免被识别
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        ]
        
        # 随机选择一个User-Agent
        self.current_agent_index = np.random.randint(0, len(self.user_agents))
        
        self.session.headers.update({
            'User-Agent': self.user_agents[self.current_agent_index],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Origin': 'https://www.eastmoney.com',
            'Referer': 'https://www.eastmoney.com/',
        })
        
        # 设置连接参数
        self.session.keep_alive = True
        self.session.verify = False  # 禁用SSL验证，避免证书问题
        
        # 设置TCP连接参数
        self.session.adapters['https://'].max_retries = retry_strategy
        self.session.timeout = 30
    
    def _rotate_user_agent(self):
        """轮换User-Agent"""
        self.current_agent_index = (self.current_agent_index + 1) % len(self.user_agents)
        self.session.headers['User-Agent'] = self.user_agents[self.current_agent_index]
        print(f"[SYNC] 切换User-Agent: {self.session.headers['User-Agent'][:50]}...")
    
    def diagnose_network(self) -> Dict:
        """诊断网络连接状态"""
        print("[FIND] 正在诊断网络连接...")
        
        results = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tests': []
        }
        
        # 测试1: 检查网络连接
        try:
            import socket
            socket.create_connection(("www.baidu.com", 80), timeout=10)
            results['tests'].append({'name': '网络连接', 'status': 'success', 'message': '网络连接正常'})
        except Exception as e:
            results['tests'].append({'name': '网络连接', 'status': 'failed', 'message': f'网络连接失败: {e}'})
        
        # 测试2: 测试东方财富网站
        try:
            response = self.session.get('https://quote.eastmoney.com/', timeout=15)
            if response.status_code == 200:
                results['tests'].append({'name': '东方财富网站', 'status': 'success', 'message': '可访问东方财富'})
            else:
                results['tests'].append({'name': '东方财富网站', 'status': 'failed', 'message': f'状态码: {response.status_code}'})
        except Exception as e:
            results['tests'].append({'name': '东方财富网站', 'status': 'failed', 'message': f'访问失败: {e}'})
        
        # 测试3: 检查代理设置
        proxy_env = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
        if proxy_env:
            results['tests'].append({'name': '代理设置', 'status': 'warning', 'message': f'检测到代理: {proxy_env}'})
        else:
            results['tests'].append({'name': '代理设置', 'status': 'success', 'message': '未使用代理'})
        
        # 打印诊断结果
        print("\n[STAT] 网络诊断报告:")
        print("-" * 50)
        for test in results['tests']:
            status_icon = "[OK]" if test['status'] == 'success' else "[WARN]" if test['status'] == 'warning' else "[ERROR]"
            print(f"{status_icon} {test['name']}: {test['message']}")
        print("-" * 50)
        
        return results
    
    def get_stock_realtime_batch(self, stock_codes: List[str] = None, use_cache: bool = True) -> pd.DataFrame:
        """
        获取股票实时行情（批量）- 支持缓存和限流检测
        :param stock_codes: 股票代码列表，None表示全部A股
        :param use_cache: 是否使用缓存
        :return: DataFrame
        """
        # 检查限流状态
        if self._check_rate_limit():
            # 如果被限流，直接返回缓存或离线数据
            cache_result = self._load_cache('stock', (tuple(sorted(stock_codes)) if stock_codes else ()))
            if cache_result is not None:
                return cache_result
            print("[STAT] 限流中，使用离线数据")
            return self._get_offline_stock_data(stock_codes)
        
        # 尝试加载缓存
        if use_cache:
            cache_result = self._load_cache('stock', (tuple(sorted(stock_codes)) if stock_codes else ()))
            if cache_result is not None:
                return cache_result
        
        # 优先使用智能快路径（东财直连，毫秒级）
        smart_df = _smart_quote(stock_codes, ['stock'])
        if smart_df is not None:
            smart_df = self._format_smart_stock(smart_df)
            if use_cache and not smart_df.empty:
                self._save_cache('stock', (tuple(sorted(stock_codes)) if stock_codes else ()), smart_df)
            return smart_df
        
        print("[STAT] 使用优先数据源策略 - 上交所/深交所优先")
        
        data_sources = [
            {'name': '上交所A股接口', 'func': ak.stock_sh_a_spot_em},
            {'name': '深交所A股接口', 'func': ak.stock_sz_a_spot_em},
            {'name': '上交所科创板接口', 'func': ak.stock_kc_a_spot_em},
            {'name': '深交所创业板接口', 'func': ak.stock_cy_a_spot_em},
            {'name': '东方财富A股接口', 'func': ak.stock_zh_a_spot_em},
            {'name': '北交所接口', 'func': ak.stock_bj_a_spot_em},
            {'name': '新股接口', 'func': ak.stock_new_a_spot_em},
        ]
        
        for source in data_sources:
            print(f"[SYNC] 尝试数据源: {source['name']}")
            try:
                df = source['func']()
                
                if df.empty:
                    print(f"[WARN] {source['name']}返回空数据")
                    continue
                
                if stock_codes:
                    df = df[df['代码'].isin(stock_codes)]
                
                # 重命名列以匹配标准
                df = self._format_stock_data(df)
                
                print(f"[OK] {source['name']}获取成功: {len(df)} 只股票")
                
                # 保存到缓存
                if use_cache and not df.empty:
                    self._save_cache('stock', (tuple(sorted(stock_codes)) if stock_codes else ()), df)
                
                return df
                
            except Exception as e:
                error_msg = str(e)[:30]
                print(f"[ERROR] {source['name']}失败: {error_msg}...")
                # 检测限流
                self._detect_rate_limit(str(e))
        
        print("[STAT] 使用离线数据（网络连接受限）")
        return self._get_offline_stock_data(stock_codes)
    
    def get_fund_realtime_batch(self, fund_codes: List[str] = None, use_cache: bool = True) -> pd.DataFrame:
        """
        获取基金实时行情（批量）- 支持缓存和限流检测
        :param fund_codes: 基金代码列表
        :param use_cache: 是否使用缓存
        :return: DataFrame
        """
        # 检查限流状态
        if self._check_rate_limit():
            cache_result = self._load_cache('fund', (tuple(sorted(fund_codes)) if fund_codes else ()))
            if cache_result is not None:
                return cache_result
            print("[STAT] 限流中，使用离线基金数据")
            return self._get_offline_fund_data(fund_codes)
        
        # 尝试加载缓存
        if use_cache:
            cache_result = self._load_cache('fund', (tuple(sorted(fund_codes)) if fund_codes else ()))
            if cache_result is not None:
                return cache_result
        
        # 优先使用智能快路径（东财直连，毫秒级）
        smart_df = _smart_quote(fund_codes, ['fund'])
        if smart_df is not None:
            smart_df = self._format_smart_fund(smart_df)
            if use_cache and not smart_df.empty:
                self._save_cache('fund', (tuple(sorted(fund_codes)) if fund_codes else ()), smart_df)
            return smart_df
        
        # 定义多个数据源，优先使用同花顺接口
        data_sources = [
            {'name': '同花顺ETF接口', 'func': ak.fund_etf_spot_ths},
            {'name': '东方财富LOF接口', 'func': ak.fund_lof_spot_em},
            {'name': '东方财富ETF接口', 'func': ak.fund_etf_spot_em},
        ]
        
        for source in data_sources:
            print(f"[SYNC] 尝试数据源: {source['name']}")
            try:
                df = source['func']()
                
                if df.empty:
                    print(f"[WARN] {source['name']}返回空数据")
                    continue
                
                if fund_codes:
                    df = df[df['代码'].isin(fund_codes)]
                
                df = self._format_fund_data(df)
                
                print(f"[OK] {source['name']}获取成功: {len(df)} 只基金")
                
                # 保存到缓存
                if use_cache and not df.empty:
                    self._save_cache('fund', (tuple(sorted(fund_codes)) if fund_codes else ()), df)
                
                return df
                
            except Exception as e:
                error_msg = str(e)[:30]
                print(f"[ERROR] {source['name']}失败: {error_msg}...")
                self._detect_rate_limit(str(e))
        
        print("[STAT] 使用离线基金数据（网络连接受限）")
        return self._get_offline_fund_data(fund_codes)
    
    def _get_offline_fund_data(self, fund_codes: List[str] = None) -> pd.DataFrame:
        """获取离线基金数据（当网络失败时使用）"""
        print("[WARN] 使用离线基金数据")
        
        # 如果没有提供基金代码，返回空DataFrame
        if not fund_codes:
            columns = ['symbol', 'name', 'price', 'change_percent', 'change_amount', 'volume', 'amount']
            return pd.DataFrame(columns=columns)
        
        # 使用列表推导创建数据，避免FutureWarning
        data = []
        for code in fund_codes:
            data.append({
                'symbol': code,
                'name': '离线数据',
                'price': 0.0,
                'change_percent': 0.0,
                'change_amount': 0.0,
                'volume': 0,
                'amount': 0
            })
        
        return pd.DataFrame(data)
    
    def get_index_realtime(self, index_codes: List[str] = None) -> pd.DataFrame:
        """
        获取指数实时行情 - 多数据源自动切换
        :param index_codes: 指数代码列表 ['000001', '399001', '000300', '399006']
        :return: DataFrame
        """
        # 默认指数列表
        default_indices = ['000001', '399001', '399006', '000300', '000016']
        if index_codes is None:
            index_codes = default_indices
        
        # 优先使用智能快路径（东财直连指数）
        smart_df = _smart_quote(index_codes, ['index'])
        if smart_df is not None:
            return self._format_smart_stock(smart_df)
        
        # 定义多个数据源（新浪接口已被封禁，只使用东方财富）
        data_sources = [
            {'name': '东方财富指数接口', 'func': ak.stock_zh_index_spot_em},
        ]
        
        for source in data_sources:
            print(f"[SYNC] 尝试数据源: {source['name']}")
            
            for attempt in range(2):
                try:
                    if attempt > 0:
                        delay = 2 + np.random.uniform(0, 1)
                        print(f"⏳ 等待 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                    
                    df = source['func']()
                    
                    if df.empty:
                        continue
                    
                    # 筛选指定指数
                    df = df[df['代码'].isin(index_codes)]
                    
                    # 重命名列以匹配标准
                    df = self._format_index_data(df)
                    
                    print(f"[OK] {source['name']}获取成功: {len(df)} 个指数")
                    return df
                    
                except Exception as e:
                    if attempt == 0:
                        print(f"[WARN] {source['name']}失败，重试中: {str(e)[:50]}...")
                    continue
            
            print(f"[ERROR] {source['name']}全部尝试失败")
        
        print("[ERROR] 所有指数数据源均失败，返回离线数据")
        return self._get_offline_index_data(index_codes)
    
    def get_concept_board_realtime(self) -> pd.DataFrame:
        """
        获取概念板块实时行情 - 使用多数据源自动切换
        :return: DataFrame
        """
        # 定义多个数据源
        data_sources = [
            {'name': '东方财富概念板块', 'func': ak.stock_board_concept_spot_em},
            {'name': '同花顺概念板块', 'func': ak.stock_board_concept_info_ths},
        ]
        
        for source in data_sources:
            print(f"[SYNC] 尝试数据源: {source['name']}")
            
            for attempt in range(2):
                try:
                    # 添加随机延迟避免被限流
                    if attempt > 0:
                        delay = 3 + attempt * 2 + np.random.uniform(0, 2)
                        print(f"⏳ 等待 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                    
                    df = source['func']()
                    
                    if df.empty:
                        continue
                    
                    # 不同数据源列名可能不同，需要适配
                    if source['name'] == '同花顺概念板块':
                        df = self._format_board_data_ths(df)
                    else:
                        df = self._format_board_data(df)
                    
                    print(f"[OK] {source['name']}获取成功: {len(df)} 个板块")
                    return df
                    
                except Exception as e:
                    if attempt == 0:
                        print(f"[WARN] {source['name']}失败，重试中: {str(e)[:50]}...")
                    continue
            
            print(f"[ERROR] {source['name']}全部尝试失败")
        
        print("[ERROR] 所有概念板块数据源均失败，返回离线数据")
        return self._get_offline_board_data()
    
    def _format_board_data_ths(self, df: pd.DataFrame) -> pd.DataFrame:
        """格式化同花顺板块数据（适配不同列名）"""
        if df.empty:
            return df
        
        # 同花顺板块数据可能有不同的列名
        column_mapping = {
            '板块名称': 'board_name',
            '概念板块': 'board_name',
            '代码': 'board_code',
            '最新价': 'price',
            '涨跌幅': 'change_percent',
            '涨跌额': 'change_amount',
            '总市值': 'total_market_cap',
            '换手率': 'turnover_rate',
            '上涨家数': 'up_count',
            '下跌家数': 'down_count',
            '领涨': 'leader_stock',
        }
        
        # 只重命名存在的列
        df_formatted = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        return df_formatted
    
    def get_industry_board_realtime(self) -> pd.DataFrame:
        """
        获取行业板块实时行情 - 使用同花顺数据源
        :return: DataFrame
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 获取行业板块数据
                df = ak.stock_board_industry_spot_em()
                
                # 重命名列以匹配同花顺标准
                df = self._format_board_data(df)
                
                print(f"[OK] 行业板块行情获取成功: {len(df)} 个板块")
                return df
                
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 行业板块网络连接失败，第{attempt+1}次重试...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"[ERROR] 获取行业板块行情失败: 网络连接错误 ({e})")
                    return self._get_offline_board_data()
                    
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 行业板块请求超时，第{attempt+1}次重试...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"[ERROR] 获取行业板块行情失败: 请求超时 ({e})")
                    return self._get_offline_board_data()
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 获取行业板块行情失败，第{attempt+1}次重试: {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[ERROR] 获取行业板块行情失败: {e}")
                    return self._get_offline_board_data()
    
    def _get_offline_board_data(self) -> pd.DataFrame:
        """获取离线板块数据（当网络失败时使用）"""
        print("[WARN] 使用离线板块数据")
        columns = ['board_name', 'board_code', 'price', 'change_percent', 'change_amount', 
                   'total_market_cap', 'turnover_rate', 'up_count', 'down_count']
        return pd.DataFrame(columns=columns)
    
    def get_market_overview_realtime(self) -> Dict:
        """
        获取市场概览（实时）- 使用同花顺数据源
        :return: dict
        """
        max_retries = 5  # 增加重试次数
        retry_delay = 3  # 秒
        
        for attempt in range(max_retries):
            try:
                # 获取实时行情（使用更稳定的接口）
                df = ak.stock_zh_a_spot()
                
                if df.empty:
                    if attempt < max_retries - 1:
                        print(f"[WARN] 市场数据为空，第{attempt+1}次重试...")
                        time.sleep(retry_delay)
                        continue
                    # 返回基础数据，避免完全失败
                    return self._get_basic_market_overview()
                
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
                    'shenzhen_index': None,
                    'hs300_index': None,
                    'gem_index': None
                }
                
                # 获取主要指数（独立处理，避免影响整体）
                self._get_index_data(overview)
                
                print("[OK] 市场概览数据获取成功（同花顺数据源）")
                return overview
                
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 网络连接失败，第{attempt+1}次重试...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"[ERROR] 获取市场概览失败: 网络连接错误 ({e})")
                    # 返回基础数据，避免完全失败
                    return self._get_basic_market_overview()
                    
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 请求超时，第{attempt+1}次重试...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"[ERROR] 获取市场概览失败: 请求超时 ({e})")
                    # 返回基础数据，避免完全失败
                    return self._get_basic_market_overview()
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 获取市场概览失败，第{attempt+1}次重试: {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[ERROR] 获取市场概览失败: {e}")
                    # 返回基础数据，避免完全失败
                    return self._get_basic_market_overview()
        
        return self._get_basic_market_overview()
    
    def _get_basic_market_overview(self) -> Dict:
        """获取基础市场概览（当网络失败时使用）"""
        return {
            'update_time': datetime.now().strftime('%H:%M:%S'),
            'total_stocks': 0,
            'up_count': 0,
            'down_count': 0,
            'flat_count': 0,
            'limit_up': 0,
            'limit_down': 0,
            'turnover': 0,
            'shanghai_index': None,
            'shenzhen_index': None,
            'hs300_index': None,
            'gem_index': None,
            'status': 'offline'
        }
    
    def _get_index_data(self, overview: Dict):
        """获取指数数据（独立处理，带重试机制）"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                index_df = ak.stock_zh_index_spot_em()
                
                # 上证指数
                sh_index = index_df[index_df['代码'] == '000001']
                if not sh_index.empty:
                    overview['shanghai_index'] = {
                        'code': '000001',
                        'name': '上证指数',
                        'price': sh_index.iloc[0]['最新价'],
                        'change': sh_index.iloc[0]['涨跌幅']
                    }
                
                # 深证成指
                sz_index = index_df[index_df['代码'] == '399001']
                if not sz_index.empty:
                    overview['shenzhen_index'] = {
                        'code': '399001',
                        'name': '深证成指',
                        'price': sz_index.iloc[0]['最新价'],
                        'change': sz_index.iloc[0]['涨跌幅']
                    }
                
                # 沪深300
                hs300_index = index_df[index_df['代码'] == '000300']
                if not hs300_index.empty:
                    overview['hs300_index'] = {
                        'code': '000300',
                        'name': '沪深300',
                        'price': hs300_index.iloc[0]['最新价'],
                        'change': hs300_index.iloc[0]['涨跌幅']
                    }
                
                # 创业板指
                gem_index = index_df[index_df['代码'] == '399006']
                if not gem_index.empty:
                    overview['gem_index'] = {
                        'code': '399006',
                        'name': '创业板指',
                        'price': gem_index.iloc[0]['最新价'],
                        'change': gem_index.iloc[0]['涨跌幅']
                    }
                return  # 成功获取，退出循环
                    
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 指数数据网络连接失败，第{attempt+1}次重试...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"[WARN] 获取指数数据失败: 网络连接错误 ({e})")
                    self._fill_default_index_data(overview)
                    
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    print(f"[WARN] 指数数据请求超时，第{attempt+1}次重试...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"[WARN] 获取指数数据失败: 请求超时 ({e})")
                    self._fill_default_index_data(overview)
                    
            except Exception as index_error:
                if attempt < max_retries - 1:
                    print(f"[WARN] 获取指数数据失败，第{attempt+1}次重试: {index_error}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[WARN] 获取指数数据失败: {index_error}")
                    self._fill_default_index_data(overview)
    
    def _fill_default_index_data(self, overview: Dict):
        """填充默认指数数据（当网络失败时使用）"""
        print("[WARN] 使用默认指数数据")
        overview['shanghai_index'] = {
            'code': '000001',
            'name': '上证指数',
            'price': 0.0,
            'change': 0.0
        }
        overview['shenzhen_index'] = {
            'code': '399001',
            'name': '深证成指',
            'price': 0.0,
            'change': 0.0
        }
        overview['hs300_index'] = {
            'code': '000300',
            'name': '沪深300',
            'price': 0.0,
            'change': 0.0
        }
        overview['gem_index'] = {
            'code': '399006',
            'name': '创业板指',
            'price': 0.0,
            'change': 0.0
        }
    
    def _get_offline_stock_data(self, stock_codes: List[str] = None) -> pd.DataFrame:
        """获取离线股票数据（当网络失败时使用）"""
        print("[WARN] 使用离线股票数据")
        
        # 如果没有提供股票代码，返回空DataFrame
        if not stock_codes:
            columns = ['symbol', 'name', 'price', 'change_percent', 'change_amount', 
                      'volume', 'amount', 'amplitude', 'high', 'low', 'open', 'pre_close', 'turnover_rate']
            return pd.DataFrame(columns=columns)
        
        # 使用列表推导创建数据，避免FutureWarning
        data = []
        for code in stock_codes:
            data.append({
                'symbol': code,
                'name': '离线数据',
                'price': 0.0,
                'change_percent': 0.0,
                'change_amount': 0.0,
                'volume': 0,
                'amount': 0,
                'amplitude': 0.0,
                'high': 0.0,
                'low': 0.0,
                'open': 0.0,
                'pre_close': 0.0,
                'turnover_rate': 0.0
            })
        
        return pd.DataFrame(data)
    
    def _get_offline_index_data(self, index_codes: List[str] = None) -> pd.DataFrame:
        """获取离线指数数据（当网络失败时使用）"""
        print("[WARN] 使用离线指数数据")
        
        # 默认指数代码
        default_indexes = ['000001', '399001', '000300', '399006']
        
        # 如果提供了指数代码，使用提供的代码，否则使用默认代码
        codes_to_use = index_codes if index_codes else default_indexes
        
        # 创建对应的离线数据
        index_names = {
            '000001': '上证指数',
            '399001': '深证成指', 
            '000300': '沪深300',
            '399006': '创业板指'
        }
        
        # 使用列表推导创建数据，避免FutureWarning
        data = []
        for code in codes_to_use:
            data.append({
                'symbol': code,
                'name': index_names.get(code, '未知指数'),
                'price': 0.0,
                'change_percent': 0.0,
                'change_amount': 0.0,
                'volume': 0,
                'amount': 0
            })
        
        return pd.DataFrame(data)
    
    def get_stock_minute_realtime(self, stock_code: str) -> pd.DataFrame:
        """
        获取股票分时数据（实时）- 使用同花顺数据源
        :param stock_code: 股票代码
        :return: DataFrame
        """
        try:
            df = ak.stock_zh_a_hist_min_em(symbol=stock_code, period='1')
            return df
        except Exception as e:
            print(f"[ERROR] 获取分时数据失败: {e}")
            return pd.DataFrame()
    
    def _format_stock_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """格式化股票数据"""
        if df.empty:
            return df
        
        # 重命名列以匹配同花顺标准
        column_mapping = {
            '代码': 'symbol',
            '名称': 'name',
            '最新价': 'price',
            '涨跌幅': 'change_percent',
            '涨跌额': 'change_amount',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '最高': 'high',
            '最低': 'low',
            '今开': 'open',
            '昨收': 'pre_close',
            '换手率': 'turnover_rate'
        }
        
        df_formatted = df.rename(columns=column_mapping)
        return df_formatted

    def _format_smart_stock(self, df: pd.DataFrame) -> pd.DataFrame:
        """智能快路径结果规整为标准股票列（symbol/name/price/...）"""
        if df.empty:
            return df
        cols = ['symbol', 'name', 'price', 'change_percent', 'change_amount', 'volume', 'amount',
                'amplitude', 'high', 'low', 'open', 'pre_close', 'turnover_rate', 'volume_ratio']
        out = df.copy()
        for c in cols:
            if c not in out.columns:
                out[c] = 0.0 if c != 'symbol' and c != 'name' else ''
        return out[cols]

    def _format_smart_fund(self, df: pd.DataFrame) -> pd.DataFrame:
        """智能快路径结果规整为标准基金列"""
        return self._format_smart_stock(df)
    
    def _format_fund_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """格式化基金数据"""
        if df.empty:
            return df
        
        # 重命名列以匹配同花顺标准
        column_mapping = {
            '代码': 'symbol',
            '名称': 'name',
            '最新价': 'price',
            '涨跌幅': 'change_percent',
            '涨跌额': 'change_amount',
            '成交量': 'volume',
            '成交额': 'amount'
        }
        
        df_formatted = df.rename(columns=column_mapping)
        return df_formatted
    
    def _format_index_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """格式化指数数据"""
        if df.empty:
            return df
        
        # 重命名列以匹配同花顺标准
        column_mapping = {
            '代码': 'symbol',
            '名称': 'name',
            '最新价': 'price',
            '涨跌幅': 'change_percent',
            '涨跌额': 'change_amount',
            '成交量': 'volume',
            '成交额': 'amount'
        }
        
        df_formatted = df.rename(columns=column_mapping)
        return df_formatted
    
    def _format_board_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """格式化板块数据"""
        if df.empty:
            return df
        
        # 重命名列以匹配同花顺标准
        column_mapping = {
            '板块名称': 'board_name',
            '板块代码': 'board_code',
            '最新价': 'price',
            '涨跌幅': 'change_percent',
            '涨跌额': 'change_amount',
            '总市值': 'total_market_cap',
            '换手率': 'turnover_rate',
            '上涨家数': 'up_count',
            '下跌家数': 'down_count'
        }
        
        df_formatted = df.rename(columns=column_mapping)
        return df_formatted
    
    # 订阅功能（保持与原有接口兼容）
    def subscribe(self, callback, symbols: List[str] = None, interval: int = 30):
        """订阅实时数据"""
        subscriber_id = f"sub_{len(self.subscribers) + 1}"
        self.subscribers[subscriber_id] = {
            'callback': callback,
            'symbols': symbols,
            'interval': interval
        }
        
        # 启动更新线程（如果未运行）
        if not self.running:
            self.start_update_loop(interval)
        
        return subscriber_id
    
    def unsubscribe(self, subscriber_id: str):
        """取消订阅"""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            
            # 如果没有订阅者，停止更新线程
            if not self.subscribers and self.running:
                self.stop_update_loop()
    
    def start_update_loop(self, interval: int = 30):
        """启动更新循环"""
        if self.running:
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, args=(interval,), daemon=True)
        self.update_thread.start()
    
    def stop_update_loop(self):
        """停止更新循环"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
    
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
                            
                            filtered_stock = stock_data[stock_data['symbol'].isin(symbols_set)] if stock_data is not None else None
                            filtered_fund = fund_data[fund_data['symbol'].isin(symbols_set)] if fund_data is not None else None
                            
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


class TonghuashunDisplay:
    """同花顺实时数据展示面板"""
    
    def __init__(self, enhancer: TonghuashunRealtimeEnhancer):
        self.enhancer = enhancer
        self.last_update = None
    
    def display_market_overview(self):
        """显示市场概览"""
        overview = self.enhancer.get_market_overview_realtime()
        
        if not overview:
            print("[ERROR] 无法获取市场概览")
            return
        
        print("\n" + "="*80)
        print(f"[STAT] 市场概览（同花顺） - {overview.get('update_time', 'N/A')}")
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
        
        if overview.get('hs300_index'):
            idx = overview['hs300_index']
            change_color = "[UP]" if idx['change'] >= 0 else "[DOWN]"
            print(f"{change_color} {idx['name']}: {idx['price']:.2f} ({idx['change']:+.2f}%)")
        
        if overview.get('gem_index'):
            idx = overview['gem_index']
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
        print(f"[UP] 股票实时行情（同花顺） - {datetime.now().strftime('%H:%M:%S')}")
        print("="*100)
        print(f"{'代码':<8} {'名称':<10} {'最新价':<10} {'涨跌幅':<10} {'涨跌额':<10} {'成交量':<12} {'成交额':<12}")
        print("-"*100)
        
        for _, row in df.iterrows():
            change_color = row['change_percent']
            change_str = f"{change_color:+.2f}%"
            
            print(f"{row['symbol']:<8} {row['name']:<10} {row['price']:<10.2f} {change_str:<10} "
                  f"{row['change_amount']:+.2f}  {row['volume']:>10,}  {row['amount']:>10,.0f}")
        
        print("="*100)
    
    def display_fund_realtime(self, fund_codes: List[str] = None):
        """显示基金实时行情"""
        df = self.enhancer.get_fund_realtime_batch(fund_codes)
        
        if df.empty:
            print("[ERROR] 无法获取基金实时行情")
            return
        
        print("\n" + "="*100)
        print(f"[MONEY] 基金实时行情（同花顺） - {datetime.now().strftime('%H:%M:%S')}")
        print("="*100)
        print(f"{'代码':<8} {'名称':<20} {'最新价':<10} {'涨跌幅':<10} {'成交量':<12} {'成交额':<12}")
        print("-"*100)
        
        for _, row in df.iterrows():
            change_color = row['change_percent']
            change_str = f"{change_color:+.2f}%"
            
            print(f"{row['symbol']:<8} {row['name']:<20} {row['price']:<10.2f} {change_str:<10} "
                  f"{row['volume']:>10,}  {row['amount']:>10,.0f}")
        
        print("="*100)
    
    def display_index_realtime(self, index_codes: List[str] = None):
        """显示指数实时行情"""
        df = self.enhancer.get_index_realtime(index_codes)
        
        if df.empty:
            print("[ERROR] 无法获取指数实时行情")
            return
        
        print("\n" + "="*80)
        print(f"[STAT] 指数实时行情（同花顺） - {datetime.now().strftime('%H:%M:%S')}")
        print("="*80)
        print(f"{'代码':<8} {'名称':<15} {'最新价':<10} {'涨跌幅':<10} {'涨跌额':<10}")
        print("-"*80)
        
        for _, row in df.iterrows():
            change_color = row['change_percent']
            change_str = f"{change_color:+.2f}%"
            
            print(f"{row['symbol']:<8} {row['name']:<15} {row['price']:<10.2f} {change_str:<10} {row['change_amount']:+.2f}")
        
        print("="*80)
    
    def display_concept_board(self):
        """显示概念板块行情"""
        df = self.enhancer.get_concept_board_realtime()
        
        if df.empty:
            print("[ERROR] 无法获取概念板块行情")
            return
        
        print("\n" + "="*100)
        print(f"🏷️ 概念板块行情（同花顺） - {datetime.now().strftime('%H:%M:%S')}")
        print("="*100)
        print(f"{'板块名称':<20} {'涨跌幅':<10} {'涨跌额':<10} {'总市值':<15} {'换手率':<10} {'上涨家数':<10}")
        print("-"*100)
        
        for _, row in df.head(20).iterrows():  # 显示前20个板块
            change_str = f"{row['change_percent']:+.2f}%"
            market_cap = f"{row['total_market_cap']/1e8:.1f}亿" if pd.notna(row['total_market_cap']) else "N/A"
            turnover = f"{row['turnover_rate']:.2f}%" if pd.notna(row['turnover_rate']) else "N/A"
            
            print(f"{row['board_name']:<20} {change_str:<10} {row['change_amount']:<10.2f} {market_cap:<15} {turnover:<10} {row['up_count']:<10}")
        
        print("="*100)


def test_tonghuashun_realtime():
    """测试同花顺实时数据功能"""
    print("="*80)
    print("🧪 测试同花顺实时数据增强功能")
    print("="*80)
    
    enhancer = TonghuashunRealtimeEnhancer()
    display = TonghuashunDisplay(enhancer)
    
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
    test_indexes = ['000001', '399001', '000300', '399006']
    display.display_index_realtime(test_indexes)
    
    # 测试5: 概念板块行情
    print("\n【测试5】获取概念板块行情...")
    display.display_concept_board()
    
    print("\n[OK] 同花顺实时数据测试完成")


if __name__ == "__main__":
    test_tonghuashun_realtime()