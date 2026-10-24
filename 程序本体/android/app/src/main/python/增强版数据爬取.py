# -*- coding: utf-8 -*-
"""
金融数据爬取程序 - 增强版
支持多种数据源和网页爬取：
1. akshare (接口数据)
2. 新浪财经 (网页爬取)
3. 东方财富 (网页爬取)
4. 雪球 (网页爬取)
5. 同花顺 (接口数据)
6. 上交所/深交所 (接口数据)

实现多数据源自动切换策略
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import requests
from bs4 import BeautifulSoup
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# 数据存储目录（相对应用目录，适配安卓沙盒）
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '金融数据')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 请求头，模拟浏览器访问
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
}

# 随机延迟，避免被封
def random_delay(min_delay=1, max_delay=3):
    """随机延迟"""
    time.sleep(random.uniform(min_delay, max_delay))


class EnhancedDataCrawler:
    """增强版金融数据爬取器 - 支持多种数据源和网页爬取"""
    
    def __init__(self, use_all_sources=True):
        """
        初始化爬虫
        :param use_all_sources: 是否使用所有数据源
        """
        self.use_all_sources = use_all_sources
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.akshare_available = False
        
        # 尝试导入akshare
        try:
            import akshare as ak
            self.ak = ak
            self.akshare_available = True
            print(f"[OK] AKShare 已加载 (版本: {ak.__version__})")
        except ImportError:
            print("[WARN] AKShare 未安装，将使用网页爬取")
        
        # 数据源优先级列表
        self.data_source_priority = [
            'sina',          # 新浪财经 - 实时数据快
            'eastmoney',     # 东方财富 - 数据全
            'xueqiu',        # 雪球 - 社区数据
            'akshare',       # akshare - 接口数据
            'ths',           # 同花顺
        ]
        
        print("[INFO] 已启用多数据源爬取策略")
    
    def _get_session(self):
        """获取会话对象，添加随机代理和请求头"""
        session = requests.Session()
        
        # 随机User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
        
        return session
    
    def _retry_request(self, url, method='GET', max_retries=3, **kwargs):
        """带重试的请求"""
        for attempt in range(max_retries):
            try:
                session = self._get_session()
                response = session.request(method, url, timeout=15, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                print(f"  请求失败 ({attempt+1}/{max_retries}): {str(e)[:50]}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
        return None
    
    def _parse_stock_code(self, stock_code):
        """解析股票代码，添加市场前缀"""
        stock_code = str(stock_code).strip()
        
        # 如果代码已经有前缀，直接返回
        if stock_code.startswith(('sh', 'sz', 'SH', 'SZ')):
            return stock_code
        
        # 根据代码判断市场
        if stock_code.startswith('6'):
            return f'sh{stock_code}'
        elif stock_code.startswith(('0', '3')):
            return f'sz{stock_code}'
        return stock_code
    
    # ==================== 新浪财经爬取 ====================
    
    def _crawl_sina_stock_data(self, stock_code, start_date, end_date):
        """从新浪财经爬取股票数据"""
        try:
            # 新浪财经接口
            code = self._parse_stock_code(stock_code)
            url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=240&ma=5,10,20&datalen=1000"
            
            print(f"    正在爬取新浪财经: {url}")
            response = self._retry_request(url)
            
            if response:
                try:
                    data = response.json()
                    if data and isinstance(data, list):
                        df = pd.DataFrame(data)
                        if not df.empty:
                            # 转换列名
                            df = df.rename(columns={
                                'day': '日期',
                                'open': '开盘',
                                'high': '最高',
                                'low': '最低',
                                'close': '收盘',
                                'volume': '成交量',
                                'amount': '成交额'
                            })
                            # 转换日期格式
                            df['日期'] = pd.to_datetime(df['日期'])
                            df = df.sort_values('日期')
                            print(f"    [OK] 新浪财经获取成功，{len(df)} 条记录")
                            return df
                except json.JSONDecodeError:
                    print("    [WARN] 新浪财经返回非JSON数据")
        except Exception as e:
            print(f"    [WARN] 新浪财经爬取失败: {str(e)[:30]}")
        return None
    
    def _crawl_sina_realtime(self, stock_code):
        """从新浪财经获取实时行情"""
        try:
            code = self._parse_stock_code(stock_code)
            url = f"http://hq.sinajs.cn/list={code}"
            
            response = self._retry_request(url)
            if response:
                content = response.text
                # 解析新浪的js格式数据
                match = re.search(r'="([^"]+)"', content)
                if match:
                    data_str = match.group(1)
                    fields = data_str.split(',')
                    if len(fields) >= 4:
                        df = pd.DataFrame({
                            '代码': [stock_code],
                            '名称': [fields[0]],
                            '最新价': [float(fields[3])],
                            '开盘': [float(fields[1])],
                            '昨收': [float(fields[2])],
                            '最高': [float(fields[4])],
                            '最低': [float(fields[5])],
                            '成交量': [int(fields[8])],
                            '成交额': [float(fields[9])],
                            '涨跌幅': [float(fields[32])],
                            '涨跌额': [float(fields[31])],
                        })
                        return df
        except Exception as e:
            print(f"    [WARN] 新浪财经实时行情获取失败: {str(e)[:30]}")
        return None
    
    # ==================== 东方财富爬取 ====================
    
    def _crawl_eastmoney_stock_data(self, stock_code, start_date, end_date):
        """从东方财富爬取股票数据"""
        try:
            code = self._parse_stock_code(stock_code).lower()
            # 东方财富接口
            url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={code}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&beg={start_date}&end={end_date}"
            
            print(f"    正在爬取东方财富: {url}")
            response = self._retry_request(url)
            
            if response:
                try:
                    data = response.json()
                    if data.get('data') and data['data'].get('klines'):
                        klines = data['data']['klines']
                        rows = []
                        for kline in klines:
                            parts = kline.split(',')
                            if len(parts) >= 6:
                                rows.append({
                                    '日期': parts[0],
                                    '开盘': float(parts[1]),
                                    '收盘': float(parts[2]),
                                    '最高': float(parts[3]),
                                    '最低': float(parts[4]),
                                    '成交量': int(parts[5]),
                                    '成交额': float(parts[6]) if len(parts) > 6 else 0,
                                })
                        df = pd.DataFrame(rows)
                        df['日期'] = pd.to_datetime(df['日期'])
                        print(f"    [OK] 东方财富获取成功，{len(df)} 条记录")
                        return df
                except json.JSONDecodeError:
                    print("    [WARN] 东方财富返回非JSON数据")
        except Exception as e:
            print(f"    [WARN] 东方财富爬取失败: {str(e)[:30]}")
        return None
    
    def _crawl_eastmoney_realtime(self, stock_code):
        """从东方财富获取实时行情"""
        try:
            code = self._parse_stock_code(stock_code).lower()
            url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={code}&fields=f57,f58,f116,f117,f118,f119,f120,f121,f122,f123,f124,f125,f126,f127,f128,f129,f130,f131,f132,f133,f134,f135,f136,f137,f138,f139,f140,f141,f142,f143,f144,f145,f146,f147,f148,f149,f150,f151,f152,f153,f154,f155,f156,f157,f158,f159,f160,f161,f162,f163,f164,f165,f166,f167,f168,f169,f170,f171,f172,f173,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f193,f194,f195,f196,f197,f198,f199,f200,f201,f202,f203,f204,f205,f206,f207,f208,f209,f210,f211,f212,f213,f214,f215,f216,f217,f218,f219,f220,f221,f222,f223,f224,f225,f226,f227,f228,f229,f230,f231,f232,f233,f234,f235,f236,f237,f238,f239,f240,f241,f242,f243,f244,f245,f246,f247,f248,f249,f250,f251,f252,f253,f254,f255,f256,f257,f258,f259,f260,f261,f262,f263,f264,f265,f266,f267,f268,f269,f270,f271,f272,f273,f274,f275,f276,f277,f278,f279,f280,f281,f282,f283,f284,f285,f286,f287,f288,f289,f290,f291,f292,f293,f294,f295,f296,f297,f298,f299,f300"
            
            response = self._retry_request(url)
            if response:
                try:
                    data = response.json()
                    if data.get('data'):
                        d = data['data']
                        df = pd.DataFrame({
                            '代码': [stock_code],
                            '名称': [d.get('f58', '')],
                            '最新价': [d.get('f57', 0)],
                            '开盘': [d.get('f116', 0)],
                            '昨收': [d.get('f117', 0)],
                            '最高': [d.get('f118', 0)],
                            '最低': [d.get('f119', 0)],
                            '成交量': [d.get('f120', 0)],
                            '成交额': [d.get('f121', 0)],
                            '涨跌幅': [d.get('f127', 0)],
                            '涨跌额': [d.get('f128', 0)],
                        })
                        return df
                except json.JSONDecodeError:
                    print("    [WARN] 东方财富实时返回非JSON数据")
        except Exception as e:
            print(f"    [WARN] 东方财富实时行情获取失败: {str(e)[:30]}")
        return None
    
    # ==================== 雪球爬取 ====================
    
    def _crawl_xueqiu_stock_data(self, stock_code, start_date, end_date):
        """从雪球爬取股票数据"""
        try:
            # 雪球的API格式
            market = 'SH' if stock_code.startswith('6') else 'SZ'
            url = f"https://stock.xueqiu.com/v5/stock/chart/kline.json?symbol={market}{stock_code}&begin={start_date}000000&period=day"
            
            print(f"    正在爬取雪球: {url}")
            response = self._retry_request(url)
            
            if response:
                try:
                    data = response.json()
                    if data.get('data') and data['data'].get('item'):
                        items = data['data']['item']
                        rows = []
                        for item in items:
                            rows.append({
                                '日期': datetime.fromtimestamp(item[0]/1000).strftime('%Y-%m-%d'),
                                '开盘': item[1],
                                '最高': item[3],
                                '最低': item[4],
                                '收盘': item[2],
                                '成交量': item[5],
                                '成交额': item[6],
                            })
                        df = pd.DataFrame(rows)
                        df['日期'] = pd.to_datetime(df['日期'])
                        print(f"    [OK] 雪球获取成功，{len(df)} 条记录")
                        return df
                except json.JSONDecodeError:
                    print("    [WARN] 雪球返回非JSON数据")
        except Exception as e:
            print(f"    [WARN] 雪球爬取失败: {str(e)[:30]}")
        return None
    
    # ==================== AKShare接口 ====================
    
    def _get_akshare_data(self, stock_code, start_date, end_date):
        """使用AKShare获取数据"""
        if not self.akshare_available:
            return None
        
        try:
            print(f"    正在使用AKShare获取数据")
            df = self.ak.stock_zh_a_hist(
                symbol=stock_code,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            if not df.empty:
                df = df.rename(columns={
                    '日期': '日期',
                    '开盘': '开盘',
                    '最高': '最高',
                    '最低': '最低',
                    '收盘': '收盘',
                    '成交量': '成交量',
                    '成交额': '成交额',
                })
                print(f"    [OK] AKShare获取成功，{len(df)} 条记录")
                return df
        except Exception as e:
            print(f"    [WARN] AKShare获取失败: {str(e)[:30]}")
        return None
    
    def _get_akshare_realtime(self, stock_code):
        """使用AKShare获取实时行情"""
        if not self.akshare_available:
            return None
        
        try:
            df = self.ak.stock_zh_a_spot_em()
            df = df[df['代码'] == stock_code]
            if not df.empty:
                return df
        except Exception as e:
            print(f"    [WARN] AKShare实时行情获取失败: {str(e)[:30]}")
        return None
    
    # ==================== 主数据获取方法 ====================
    
    def get_stock_daily(self, stock_code, start_date=None, end_date=None):
        """
        获取股票日线数据 - 多数据源自动切换
        :param stock_code: 股票代码
        :param start_date: 开始日期 (格式: '20200101')
        :param end_date: 结束日期
        :return: DataFrame
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        print(f"\n[SYNC] 获取股票 {stock_code} 数据 ({start_date} - {end_date})")
        
        # 定义数据源爬取函数
        sources = [
            ('新浪财经', lambda: self._crawl_sina_stock_data(stock_code, start_date, end_date)),
            ('东方财富', lambda: self._crawl_eastmoney_stock_data(stock_code, start_date, end_date)),
            ('雪球', lambda: self._crawl_xueqiu_stock_data(stock_code, start_date, end_date)),
            ('AKShare', lambda: self._get_akshare_data(stock_code, start_date, end_date)),
        ]
        
        # 并行尝试所有数据源
        results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for name, func in sources:
                future = executor.submit(func)
                futures[future] = name
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    if result is not None and not result.empty:
                        results[name] = result
                except Exception as e:
                    print(f"    [ERROR] {name} 执行失败: {str(e)[:30]}")
        
        # 选择最佳数据源（优先选择数据最新的）
        if results:
            best_source = None
            best_df = None
            max_rows = 0
            
            for name, df in results.items():
                row_count = len(df)
                print(f"    {name}: {row_count} 条数据")
                if row_count > max_rows:
                    max_rows = row_count
                    best_source = name
                    best_df = df
            
            print(f"[OK] 选择 {best_source} 数据源，共 {len(best_df)} 条记录")
            return self._normalize_dataframe(best_df)
        
        # 所有数据源都失败
        print(f"[ERROR] 所有数据源都无法获取 {stock_code} 数据")
        return pd.DataFrame()
    
    def get_stock_realtime(self, stock_codes):
        """
        获取股票实时行情 - 多数据源并行获取
        :param stock_codes: 股票代码列表
        :return: DataFrame
        """
        print(f"\n[SYNC] 获取 {len(stock_codes)} 只股票实时行情")
        
        all_results = []
        
        # 并行获取每只股票的实时数据
        def fetch_one(code):
            sources = [
                ('新浪财经', lambda: self._crawl_sina_realtime(code)),
                ('东方财富', lambda: self._crawl_eastmoney_realtime(code)),
                ('AKShare', lambda: self._get_akshare_realtime(code)),
            ]
            
            for name, func in sources:
                try:
                    df = func()
                    if df is not None and not df.empty:
                        print(f"    {code}: {name} 获取成功")
                        return df
                except Exception as e:
                    pass
            print(f"    {code}: 所有数据源失败")
            return None
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_one, code): code for code in stock_codes}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    all_results.append(result)
        
        if all_results:
            df = pd.concat(all_results, ignore_index=True)
            print(f"[OK] 成功获取 {len(df)} 只股票实时行情")
            return df
        return pd.DataFrame()
    
    def _normalize_dataframe(self, df):
        """标准化DataFrame格式"""
        if df is None or df.empty:
            return df
        
        # 确保日期列存在且格式正确
        if '日期' not in df.columns:
            if 'date' in df.columns:
                df = df.rename(columns={'date': '日期'})
            elif len(df) > 0:
                df['日期'] = pd.date_range(start='2020-01-01', periods=len(df), freq='D')
        
        # 确保必要的列存在
        required_cols = ['日期', '开盘', '最高', '最低', '收盘', '成交量', '成交额']
        for col in required_cols:
            if col not in df.columns:
                if col == '成交量':
                    df[col] = 0
                elif col == '成交额':
                    df[col] = 0.0
                elif col in ['开盘', '最高', '最低', '收盘']:
                    if '收盘' in df.columns:
                        df[col] = df['收盘']
                    else:
                        df[col] = 0.0
        
        # 转换日期格式
        df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
        
        # 排序
        df = df.sort_values('日期')
        
        return df
    
    def save_to_csv(self, data, filename):
        """保存数据到CSV"""
        if not data.empty:
            filepath = os.path.join(DATA_DIR, filename)
            data.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"数据已保存到: {filepath}")
        else:
            print("数据为空，未保存")
    
    def batch_download(self, stock_codes, start_date=None, end_date=None):
        """
        批量下载股票数据
        :param stock_codes: 股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 数据字典
        """
        all_data = {}
        success_count = 0
        fail_count = 0
        
        print(f"\n[SYNC] 开始批量下载 {len(stock_codes)} 只股票")
        
        for code in stock_codes:
            print(f"\n[{success_count + fail_count + 1}/{len(stock_codes)}] {code}")
            
            df = self.get_stock_daily(code, start_date, end_date)
            
            if not df.empty:
                all_data[code] = df
                self.save_to_csv(df, f"{code}_日线数据.csv")
                success_count += 1
                print(f"[OK] {code} 下载成功")
            else:
                fail_count += 1
                print(f"[FAIL] {code} 下载失败")
            
            # 随机延迟
            random_delay(0.5, 1.5)
        
        print(f"\n[DONE] 批量下载完成: 成功 {success_count} | 失败 {fail_count}")
        return all_data
    
    def get_market_overview(self):
        """获取市场概览"""
        overview = {}
        
        # 尝试从多个数据源获取市场概览
        try:
            if self.akshare_available:
                df = self.ak.stock_zh_a_spot_em()
                overview['总股票数'] = len(df)
                overview['上涨数'] = len(df[df['涨跌幅'] > 0])
                overview['下跌数'] = len(df[df['涨跌幅'] < 0])
                overview['平盘数'] = len(df[df['涨跌幅'] == 0])
                overview['涨停数'] = len(df[df['涨跌幅'] >= 9.9])
                overview['跌停数'] = len(df[df['涨跌幅'] <= -9.9])
                print("[OK] 市场概览获取成功")
        except Exception as e:
            print(f"[WARN] 市场概览获取失败: {e}")
        
        return overview
    
    def get_hot_stocks(self, top_n=20):
        """获取热门股票"""
        try:
            if self.akshare_available:
                df = self.ak.stock_zh_a_spot_em()
                df = df.sort_values(by='涨跌幅', ascending=False).head(top_n)
                return df
        except Exception as e:
            print(f"[WARN] 热门股票获取失败: {e}")
        return pd.DataFrame()


# ==================== 测试函数 ====================

def test_crawler():
    """测试爬虫功能"""
    print("=" * 60)
    print("测试增强版数据爬取器")
    print("=" * 60)
    
    crawler = EnhancedDataCrawler()
    
    # 测试股票列表
    test_stocks = ['600519', '000858', '601318']
    
    # 测试获取单只股票数据
    print("\n1. 测试获取单只股票数据:")
    df = crawler.get_stock_daily('600519')
    if not df.empty:
        print(f"   成功获取 {len(df)} 条数据")
        print(df.head())
    
    # 测试实时行情
    print("\n2. 测试获取实时行情:")
    realtime_df = crawler.get_stock_realtime(test_stocks)
    if not realtime_df.empty:
        print(f"   成功获取 {len(realtime_df)} 只股票实时数据")
        print(realtime_df[['代码', '名称', '最新价', '涨跌幅']])
    
    # 测试市场概览
    print("\n3. 测试获取市场概览:")
    overview = crawler.get_market_overview()
    if overview:
        for key, value in overview.items():
            print(f"   {key}: {value}")
    
    # 测试批量下载
    print("\n4. 测试批量下载:")
    result = crawler.batch_download(test_stocks)
    print(f"   成功下载 {len(result)} 只股票")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_crawler()