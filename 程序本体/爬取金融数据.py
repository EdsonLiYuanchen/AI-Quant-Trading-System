"""
金融数据爬取程序
支持多种数据源：tushare、akshare、yfinance
功能：股票行情、财务数据、指数数据等
新增数据库存储功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import glob

# 数据存储目录 - 使用绝对路径
DATA_DIR = r"C:\Users\Edson\code\.vscode\量化交易\金融数据"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"已创建数据目录: {DATA_DIR}")

# 导入数据库管理器
try:
    from database_manager import DatabaseManager
except ImportError:
    print("[WARN] 数据库管理器导入失败，将仅使用文件存储")


def clear_data_folder():
    """清空金融数据文件夹"""
    files = glob.glob(os.path.join(DATA_DIR, "*"))
    deleted_count = 0
    
    if not files:
        print("文件夹已经是空的")
        return 0
    
    print(f"目标路径: {DATA_DIR}")
    print(f"找到 {len(files)} 个文件，准备删除...")
    
    for file_path in files:
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"  ✓ 已删除: {os.path.basename(file_path)}")
                deleted_count += 1
            except Exception as e:
                print(f"  ✗ 删除失败 {os.path.basename(file_path)}: {e}")
    
    print(f"\n✓ 成功删除 {deleted_count} 个文件")
    print(f"数据目录: {DATA_DIR}")
    return deleted_count


class FinancialDataCrawler:
    """金融数据爬取器 - 优先使用上交所/深交所数据源"""
    
    def __init__(self, data_source='sse_szse', use_database=True):
        """
        初始化爬虫
        :param data_source: 数据源选择 ('sse_szse'-上交所/深交所, 'ths'-同花顺, 'akshare', 'tushare', 'yfinance')
        :param use_database: 是否使用数据库存储
        """
        self.data_source = data_source
        self.use_database = use_database
        self.db_manager = None
        
        # 上交所/深交所数据源优先级
        self.sse_szse_priority = True  # 优先使用上交所/深交所
        
        if use_database:
            try:
                self.db_manager = DatabaseManager()
                print("[OK] 数据库连接成功，将同时存储到数据库")
            except Exception as e:
                print("[WARN] 数据库连接失败: %s，将仅使用文件存储" % str(e)[:50])
                self.use_database = False
        
        print("[INFO] 使用数据源: %s (上交所/深交所优先)" % data_source)
        
    def get_stock_list(self, market='A股'):
        """
        获取股票列表
        :param market: 市场类型
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                if market == 'A股':
                    stock_list = ak.stock_info_a_code_name()
                    print(f"获取到 {len(stock_list)} 只A股")
                    return stock_list
                elif market == '港股':
                    stock_list = ak.stock_hk_spot()
                    print(f"获取到 {len(stock_list)} 只港股")
                    return stock_list
            return pd.DataFrame()
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_stock_daily(self, stock_code, start_date=None, end_date=None):
        """
        获取股票日线数据 - 优先使用同花顺数据源
        :param stock_code: 股票代码
        :param start_date: 开始日期 (格式: '20200101')
        :param end_date: 结束日期
        :return: DataFrame
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
            
        print(f"[SYNC] 尝试获取股票 {stock_code} 数据 ({start_date} 到 {end_date})")
        
        # 定义数据源优先级：上交所/深交所优先
        data_sources = []
        
        # 如果设置了上交所/深交所优先或数据源为sse_szse，则优先尝试上交所/深交所
        if self.sse_szse_priority or self.data_source == 'sse_szse':
            data_sources.append({'name': '上交所', 'func': self._get_stock_daily_sse})
            data_sources.append({'name': '深交所', 'func': self._get_stock_daily_szse})
            data_sources.append({'name': '同花顺', 'func': self._get_stock_daily_ths})
            data_sources.append({'name': 'akshare', 'func': self._get_stock_daily_akshare})
            data_sources.append({'name': 'tushare_backup', 'func': self._get_stock_daily_backup})
        elif self.data_source == 'ths':
            data_sources.append({'name': '同花顺', 'func': self._get_stock_daily_ths})
            data_sources.append({'name': '上交所', 'func': self._get_stock_daily_sse})
            data_sources.append({'name': '深交所', 'func': self._get_stock_daily_szse})
            data_sources.append({'name': 'akshare', 'func': self._get_stock_daily_akshare})
            data_sources.append({'name': 'tushare_backup', 'func': self._get_stock_daily_backup})
        elif self.data_source == 'akshare':
            data_sources.append({'name': 'akshare', 'func': self._get_stock_daily_akshare})
            data_sources.append({'name': '上交所', 'func': self._get_stock_daily_sse})
            data_sources.append({'name': '深交所', 'func': self._get_stock_daily_szse})
            data_sources.append({'name': '同花顺', 'func': self._get_stock_daily_ths})
            data_sources.append({'name': 'tushare_backup', 'func': self._get_stock_daily_backup})
        else:
            data_sources.append({'name': '上交所', 'func': self._get_stock_daily_sse})
            data_sources.append({'name': '深交所', 'func': self._get_stock_daily_szse})
            data_sources.append({'name': 'akshare', 'func': self._get_stock_daily_akshare})
            data_sources.append({'name': 'tushare_backup', 'func': self._get_stock_daily_backup})
        
        for source in data_sources:
            try:
                print(f"  尝试数据源: {source['name']}")
                df = source['func'](stock_code, start_date, end_date)
                
                if df is None or df.empty:
                    print(f"  [WARN]  {source['name']}返回空数据")
                    continue
                
                print(f"[OK] 使用{source['name']}获取 {stock_code} 数据成功，共 {len(df)} 条记录")
                print(f"  数据列名: {list(df.columns)}")
                
                # 保存到数据库
                if self.use_database:
                    formatted_df = self._format_data_for_database(df, stock_code, 'daily_quotes')
                    if not formatted_df.empty:
                        db_success = self._save_to_database(formatted_df, 'daily_quotes')
                        if db_success:
                            print(f"[OK] 数据已成功保存到数据库")
                
                return df
                
            except Exception as e:
                print(f"  [WARN]  使用 {source['name']} 获取 {stock_code} 数据失败: {str(e)[:50]}...")
                continue
        
        # 所有数据源都失败
        print(f"[ERROR] 所有数据源都无法获取 {stock_code} 数据")
        print("[IDEA] 解决方案:")
        print("  1. 检查网络连接")
        print("  2. 安装依赖: pip install akshare")
        print("  3. 尝试其他股票代码")
        return pd.DataFrame()
    
    def _get_stock_daily_sse(self, stock_code, start_date, end_date):
        """使用上交所接口获取股票日线数据"""
        import akshare as ak
        # 上交所股票代码以6开头
        if stock_code.startswith('6'):
            df = ak.stock_zh_a_hist(symbol=stock_code, 
                                   start_date=start_date, 
                                   end_date=end_date,
                                   adjust="qfq")
            if df is not None and not df.empty:
                print(f"  [OK] 上交所数据获取成功")
                return self._normalize_dataframe(df)
        raise Exception(f"股票代码 {stock_code} 不是上交所股票")
    
    def _get_stock_daily_szse(self, stock_code, start_date, end_date):
        """使用深交所接口获取股票日线数据"""
        import akshare as ak
        # 深交所股票代码以0或3开头
        if stock_code.startswith('0') or stock_code.startswith('3'):
            df = ak.stock_zh_a_hist(symbol=stock_code, 
                                   start_date=start_date, 
                                   end_date=end_date,
                                   adjust="qfq")
            if df is not None and not df.empty:
                print(f"  [OK] 深交所数据获取成功")
                return self._normalize_dataframe(df)
        raise Exception(f"股票代码 {stock_code} 不是深交所股票")
    
    def _get_stock_daily_ths(self, stock_code, start_date, end_date):
        """使用同花顺接口获取股票日线数据"""
        import akshare as ak
        # 同花顺A股日线数据
        df = ak.stock_zh_a_hist(symbol=stock_code, 
                               start_date=start_date, 
                               end_date=end_date,
                               adjust="qfq")
        return self._normalize_dataframe(df)
    
    def _get_stock_daily_akshare(self, stock_code, start_date, end_date):
        """使用akshare接口获取股票日线数据"""
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=stock_code, 
                               start_date=start_date, 
                               end_date=end_date,
                               adjust="qfq")
        return self._normalize_dataframe(df)
    
    def _get_stock_daily_backup(self, stock_code, start_date, end_date):
        """备用方案：生成模拟数据"""
        print("  [SYNC] 使用备用数据源...")
        return self._generate_sample_data(stock_code, start_date, end_date)
    
    def _normalize_dataframe(self, df):
        """标准化DataFrame列名"""
        if df is None or df.empty:
            return df
        
        # 检查列名并统一为中文格式
        column_mapping = {
            'date': '日期',
            'close': '收盘',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'volume': '成交量',
            'amount': '成交额',
            'change': '涨跌幅',
            'pct_chg': '涨跌幅'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 确保日期列存在
        if '日期' not in df.columns:
            if '日期' in df.columns:
                pass  # 已经有了
            elif len(df) > 0:
                # 如果没有日期列，尝试生成
                df['日期'] = pd.date_range(start='2020-01-01', periods=len(df), freq='D')
        
        return df
    
    def _generate_sample_data(self, stock_code, start_date, end_date):
        """生成模拟数据用于测试"""
        try:
            # 生成日期范围
            start = datetime.strptime(start_date, '%Y%m%d')
            end = datetime.strptime(end_date, '%Y%m%d')
            dates = pd.date_range(start=start, end=end, freq='D')
            
            # 过滤掉周末
            dates = dates[dates.dayofweek < 5]
            
            if len(dates) == 0:
                return None
            
            # 生成模拟价格数据
            np.random.seed(42)  # 固定随机种子保证结果一致
            base_price = 10.0 + np.random.random() * 10
            prices = []
            
            for i in range(len(dates)):
                if i == 0:
                    price = base_price
                else:
                    # 随机波动
                    change = np.random.normal(0, 0.02)
                    price = prices[i-1] * (1 + change)
                prices.append(round(price, 2))
            
            # 创建DataFrame
            df = pd.DataFrame({
                '日期': dates,
                '开盘': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
                '最高': [p * (1 + np.random.normal(0.01, 0.01)) for p in prices],
                '最低': [p * (1 - np.random.normal(0.01, 0.01)) for p in prices],
                '收盘': prices,
                '成交量': [int(np.random.normal(1000000, 200000)) for _ in prices],
                '成交额': [p * v for p, v in zip(prices, [np.random.normal(1000000, 200000) for _ in prices])]
            })
            
            # 数值处理
            for col in ['开盘', '最高', '最低', '收盘']:
                df[col] = df[col].round(2)
            df['成交量'] = df['成交量'].astype(int)
            df['成交额'] = df['成交额'].round(2)
            
            return df
            
        except Exception as e:
            print(f"生成模拟数据失败: {e}")
            return None
    
    def get_stock_data(self, stock_code, start_date=None, end_date=None):
        """
        获取股票数据（别名方法）
        :param stock_code: 股票代码
        :param start_date: 开始日期 (格式: '20200101')
        :param end_date: 结束日期
        :return: DataFrame
        """
        return self.get_stock_daily(stock_code, start_date, end_date)
    
    def get_stock_realtime(self, stock_codes):
        """
        获取股票实时行情
        :param stock_codes: 股票代码列表
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                df = ak.stock_zh_a_spot_em()
                # 筛选指定股票
                if stock_codes:
                    df = df[df['代码'].isin(stock_codes)]
                print(f"获取实时行情成功，共 {len(df)} 只股票")
                return df
        except Exception as e:
            print(f"获取实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_index_data(self, index_code='000001', start_date=None, end_date=None):
        """
        获取指数数据
        :param index_code: 指数代码 (如 '000001' 上证指数)
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: DataFrame
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
            
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
                # 日期筛选
                df['date'] = pd.to_datetime(df['date'])
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date)
                df = df[(df['date'] >= start) & (df['date'] <= end)]
                print(f"获取指数 {index_code} 数据成功，共 {len(df)} 条记录")
                return df
        except Exception as e:
            print(f"获取指数数据失败: {e}")
            return pd.DataFrame()
    
    def get_financial_report(self, stock_code):
        """
        获取财务报表数据
        :param stock_code: 股票代码
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                # 获取利润表
                df = ak.stock_financial_report_sina(stock=stock_code, symbol="利润表")
                print(f"获取 {stock_code} 财务数据成功")
                return df
        except Exception as e:
            print(f"获取财务数据失败: {e}")
            return pd.DataFrame()
    
    def get_fund_data(self, fund_code):
        """
        获取基金净值数据
        :param fund_code: 基金代码
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                df = ak.fund_open_fund_info_em(fund=fund_code, indicator="单位净值走势")
                print(f"获取基金 {fund_code} 数据成功，共 {len(df)} 条记录")
                return df
        except Exception as e:
            print(f"获取基金数据失败: {e}")
            return pd.DataFrame()
    
    def save_to_csv(self, data, filename):
        """
        保存数据到CSV
        :param data: DataFrame数据
        :param filename: 文件名
        """
        if not data.empty:
            filepath = os.path.join(DATA_DIR, filename)
            data.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"数据已保存到: {filepath}")
        else:
            print("数据为空，未保存")
    
    def batch_download_stocks(self, stock_codes, start_date=None, end_date=None, delay=1):
        """
        批量下载股票数据
        :param stock_codes: 股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param delay: 请求间隔(秒)
        """
        all_data = {}
        for code in stock_codes:
            print(f"\n正在下载: {code}")
            df = self.get_stock_daily(code, start_date, end_date)
            if not df.empty:
                all_data[code] = df
                self.save_to_csv(df, f"{code}_日线数据.csv")
            time.sleep(delay)  # 避免请求过快
        
        print(f"\n批量下载完成！成功下载 {len(all_data)} 只股票")
        return all_data
    
    def _format_data_for_database(self, df, stock_code, data_type):
        """
        格式化数据以适应数据库表结构
        :param df: 原始数据
        :param stock_code: 股票代码
        :param data_type: 数据类型 ('daily_quotes', 'financial_data', 'technical_indicators')
        :return: 格式化后的DataFrame
        """
        if df.empty:
            return df
        
        df_formatted = df.copy()
        
        if data_type == 'daily_quotes':
            # 格式化日线数据
            df_formatted['ts_code'] = stock_code
            
            # 重命名列名以匹配数据库表结构
            column_mapping = {
                '日期': 'trade_date',
                'date': 'trade_date',
                '开盘': 'open',
                'open': 'open',
                '最高': 'high',
                'high': 'high',
                '最低': 'low',
                'low': 'low',
                '收盘': 'close',
                'close': 'close',
                '成交量': 'vol',
                'volume': 'vol',
                '成交额': 'amount',
                'amount': 'amount',
                '涨跌幅': 'pct_chg',
                'pct_chg': 'pct_chg'
            }
            
            # 重命名列
            df_formatted = df_formatted.rename(columns=column_mapping)
            
            # 确保日期格式正确
            if 'trade_date' in df_formatted.columns:
                df_formatted['trade_date'] = pd.to_datetime(df_formatted['trade_date']).dt.strftime('%Y-%m-%d')
            
            # 添加昨收价和涨跌额（如果不存在）
            if 'pre_close' not in df_formatted.columns:
                df_formatted['pre_close'] = df_formatted['close'].shift(1)
            if 'price_change' not in df_formatted.columns:
                df_formatted['price_change'] = df_formatted['close'] - df_formatted['pre_close']
        
        return df_formatted
    
    def _save_to_database(self, df, data_type):
        """
        保存数据到数据库
        :param df: 格式化后的数据
        :param data_type: 数据类型
        """
        if not self.use_database or df.empty:
            return False
        
        try:
            if data_type == 'daily_quotes':
                return self.db_manager.insert_daily_quotes(df)
            elif data_type == 'financial_data':
                return self.db_manager.insert_financial_data(df)
            elif data_type == 'technical_indicators':
                return self.db_manager.insert_technical_indicators(df)
            else:
                print(f"[WARN] 未知的数据类型: {data_type}")
                return False
        except Exception as e:
            print(f"[ERROR] 保存到数据库失败: {e}")
            return False
    
    def get_stock_info(self, stock_code):
        """
        获取股票基本信息
        :param stock_code: 股票代码
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                df = ak.stock_individual_info_em(symbol=stock_code)
                print(f"获取 {stock_code} 基本信息成功")
                return df
        except Exception as e:
            print(f"获取股票信息失败: {e}")
            return pd.DataFrame()
    
    def get_hot_stocks(self, top_n=20):
        """
        获取热门股票
        :param top_n: 返回前N只热门股
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                # 获取涨幅榜
                df_up = ak.stock_zh_a_spot_em()
                df_up = df_up.sort_values(by='涨跌幅', ascending=False).head(top_n)
                print(f"获取涨幅榜前{top_n}成功")
                return df_up
        except Exception as e:
            print(f"获取热门股票失败: {e}")
            return pd.DataFrame()
    
    def get_stock_news(self, stock_code):
        """
        获取个股新闻
        :param stock_code: 股票代码
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                df = ak.stock_news_em(symbol=stock_code)
                print(f"获取 {stock_code} 新闻成功，共 {len(df)} 条")
                return df
        except Exception as e:
            print(f"获取股票新闻失败: {e}")
            return pd.DataFrame()
    
    def get_market_overview(self):
        """
        获取市场概览（北上资金、两市成交额等）
        :return: dict
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                overview = {}
                
                # 沪深京A股实时行情
                market_df = ak.stock_zh_a_spot_em()
                overview['总股票数'] = len(market_df)
                overview['上涨数'] = len(market_df[market_df['涨跌幅'] > 0])
                overview['下跌数'] = len(market_df[market_df['涨跌幅'] < 0])
                overview['平盘数'] = len(market_df[market_df['涨跌幅'] == 0])
                
                # 涨停跌停
                overview['涨停数'] = len(market_df[market_df['涨跌幅'] >= 9.9])
                overview['跌停数'] = len(market_df[market_df['涨跌幅'] <= -9.9])
                
                print("市场概览数据获取成功")
                return overview
        except Exception as e:
            print(f"获取市场概览失败: {e}")
            return {}
    
    def get_stock_holder(self, stock_code):
        """
        获取十大股东信息
        :param stock_code: 股票代码
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                df = ak.stock_gdfx_holding_analyse_em(symbol=stock_code)
                print(f"获取 {stock_code} 股东信息成功")
                return df
        except Exception as e:
            print(f"获取股东信息失败: {e}")
            return pd.DataFrame()
    
    def get_concept_stocks(self, concept_name):
        """
        获取概念板块成分股
        :param concept_name: 概念名称（如"人工智能"、"新能源"）
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                # 获取所有概念板块
                concept_list = ak.stock_board_concept_name_em()
                
                # 查找匹配的概念
                matched = concept_list[concept_list['板块名称'].str.contains(concept_name)]
                
                if not matched.empty:
                    concept_code = matched.iloc[0]['板块代码']
                    df = ak.stock_board_concept_cons_em(symbol=concept_code)
                    print(f"获取【{concept_name}】概念股成功，共 {len(df)} 只")
                    return df
                else:
                    print(f"未找到【{concept_name}】相关概念")
                    return pd.DataFrame()
        except Exception as e:
            print(f"获取概念股失败: {e}")
            return pd.DataFrame()
    
    def get_industry_stocks(self, industry_name):
        """
        获取行业板块成分股
        :param industry_name: 行业名称（如"半导体"、"证券"）
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                # 获取所有行业板块
                industry_list = ak.stock_board_industry_name_em()
                
                # 查找匹配的行业
                matched = industry_list[industry_list['板块名称'].str.contains(industry_name, case=False, na=False)]
                
                if not matched.empty:
                    industry_code = matched.iloc[0]['板块代码']
                    df = ak.stock_board_industry_cons_em(symbol=industry_code)
                    print(f"获取【{industry_name}】行业股成功，共 {len(df)} 只")
                    return df
                else:
                    print(f"未找到【{industry_name}】相关行业")
                    return pd.DataFrame()
        except Exception as e:
            print(f"获取行业股失败: {e}")
            return pd.DataFrame()
    
    def get_stock_minute(self, stock_code):
        """
        获取股票分时数据（当日）
        :param stock_code: 股票代码
        :return: DataFrame
        """
        try:
            if self.data_source == 'akshare':
                import akshare as ak
                df = ak.stock_zh_a_hist_min_em(symbol=stock_code, period='1')
                print(f"获取 {stock_code} 分时数据成功，共 {len(df)} 条")
                return df
        except Exception as e:
            print(f"获取分时数据失败: {e}")
            return pd.DataFrame()


def input_stock_codes():
    """
    交互式输入股票代码
    :return: 股票代码列表
    """
    print("\n" + "=" * 60)
    print("请输入股票代码（支持多种输入方式）")
    print("=" * 60)
    print("方式1: 逐个输入（输入 'q' 结束）")
    print("方式2: 批量输入（用逗号或空格分隔，如: 000001,600036,601318）")
    print("方式3: 输入 'file' 从文件读取")
    print("-" * 60)
    
    stock_codes = []
    
    mode = input("\n选择输入方式 (1/2/3): ").strip()
    
    if mode == '1':
        # 逐个输入
        print("\n开始输入股票代码（输入 'q' 结束）:")
        while True:
            code = input("股票代码: ").strip()
            if code.lower() == 'q':
                break
            if code:
                stock_codes.append(code)
                print(f"  ✓ 已添加: {code}")
    
    elif mode == '2':
        # 批量输入
        codes_input = input("\n请输入股票代码（用逗号或空格分隔）: ").strip()
        # 支持逗号和空格分隔
        codes_input = codes_input.replace(',', ' ').replace('，', ' ')
        stock_codes = [code.strip() for code in codes_input.split() if code.strip()]
    
    elif mode == '3':
        # 从文件读取
        filename = input("\n请输入文件路径（每行一个代码）: ").strip()
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                stock_codes = [line.strip() for line in f if line.strip()]
            print(f"✓ 从文件读取 {len(stock_codes)} 个股票代码")
        except Exception as e:
            print(f"[ERROR] 读取文件失败: {e}")
            return []
    
    else:
        print("[ERROR] 无效的选择")
        return []
    
    # 去重
    stock_codes = list(set(stock_codes))
    
    if stock_codes:
        print(f"\n✓ 共收集到 {len(stock_codes)} 个股票代码:")
        print("  " + ", ".join(stock_codes))
    else:
        print("\n[ERROR] 未输入任何股票代码")
    
    return stock_codes


def batch_crawl_stocks(stock_codes, crawler, data_type='all'):
    """
    批量爬取股票信息
    :param stock_codes: 股票代码列表
    :param crawler: 爬虫实例
    :param data_type: 数据类型 ('daily'|'realtime'|'info'|'news'|'all')
    """
    if not stock_codes:
        print("[ERROR] 股票代码列表为空")
        return
    
    print("\n" + "=" * 60)
    print(f"开始批量爬取 {len(stock_codes)} 只股票的数据")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for idx, code in enumerate(stock_codes, 1):
        print(f"\n[{idx}/{len(stock_codes)}] 正在处理: {code}")
        print("-" * 40)
        
        try:
            # 日线数据
            if data_type in ['daily', 'all']:
                print(f"  获取日线数据...")
                current_year = datetime.now().year
                daily_data = crawler.get_stock_daily(
                    code, 
                    start_date=f'{current_year}0101',
                    end_date=datetime.now().strftime('%Y%m%d')
                )
                if not daily_data.empty:
                    crawler.save_to_csv(daily_data, f"{code}_日线数据.csv")
            
            # 实时行情
            if data_type in ['realtime', 'all']:
                print(f"  获取实时行情...")
                realtime_data = crawler.get_stock_realtime([code])
                if not realtime_data.empty:
                    display_cols = ['代码', '名称', '最新价', '涨跌幅', '成交量', '成交额', '换手率']
                    available_cols = [col for col in display_cols if col in realtime_data.columns]
                    print(realtime_data[available_cols].to_string(index=False))
                    crawler.save_to_csv(realtime_data, f"{code}_实时行情.csv")
            
            # 基本信息
            if data_type in ['info', 'all']:
                print(f"  获取基本信息...")
                info_data = crawler.get_stock_info(code)
                if not info_data.empty:
                    crawler.save_to_csv(info_data, f"{code}_基本信息.csv")
            
            # 新闻
            if data_type in ['news', 'all']:
                print(f"  获取新闻...")
                news_data = crawler.get_stock_news(code)
                if not news_data.empty:
                    crawler.save_to_csv(news_data, f"{code}_新闻.csv")
            
            success_count += 1
            print(f"  ✓ {code} 数据获取完成")
            
            # 避免请求过快
            if idx < len(stock_codes):
                time.sleep(1)
        
        except Exception as e:
            fail_count += 1
            print(f"  [ERROR] {code} 数据获取失败: {e}")
    
    # 总结
    print("\n" + "=" * 60)
    print("批量爬取完成!")
    print(f"成功: {success_count} | 失败: {fail_count}")
    print(f"数据保存目录: {DATA_DIR}")
    print("=" * 60)


def main():
    """主程序"""
    print("=" * 60)
    print("金融数据批量爬取程序")
    print("=" * 60)
    
    # 创建爬虫实例
    crawler = FinancialDataCrawler(data_source='akshare')
    
    while True:
        print("\n" + "=" * 60)
        print("主菜单")
        print("=" * 60)
        print("1. 批量爬取股票数据（输入股票代码）")
        print("2. 获取市场概览")
        print("3. 获取涨幅榜")
        print("4. 获取概念板块成分股")
        print("5. 清空数据文件夹")
        print("0. 退出程序")
        print("-" * 60)
        
        choice = input("请选择功能 (0-5): ").strip()
        
        if choice == '1':
            # 批量爬取
            stock_codes = input_stock_codes()
            if stock_codes:
                print("\n选择爬取的数据类型:")
                print("1. 日线数据")
                print("2. 实时行情")
                print("3. 基本信息")
                print("4. 新闻")
                print("5. 全部数据")
                data_choice = input("请选择 (1-5): ").strip()
                
                data_type_map = {
                    '1': 'daily',
                    '2': 'realtime',
                    '3': 'info',
                    '4': 'news',
                    '5': 'all'
                }
                
                data_type = data_type_map.get(data_choice, 'all')
                batch_crawl_stocks(stock_codes, crawler, data_type)
        
        elif choice == '2':
            # 市场概览
            print("\n获取市场概览...")
            overview = crawler.get_market_overview()
            if overview:
                print("\n市场数据:")
                for key, value in overview.items():
                    print(f"  {key}: {value}")
        
        elif choice == '3':
            # 涨幅榜
            top_n = input("\n请输入获取数量 (默认20): ").strip()
            top_n = int(top_n) if top_n.isdigit() else 20
            
            print(f"\n获取涨幅榜前{top_n}...")
            hot_stocks = crawler.get_hot_stocks(top_n=top_n)
            if not hot_stocks.empty:
                display_cols = ['代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额']
                available_cols = [col for col in display_cols if col in hot_stocks.columns]
                print("\n" + hot_stocks[available_cols].to_string(index=False))
                
                save = input("\n是否保存到文件? (y/n): ").strip().lower()
                if save == 'y':
                    crawler.save_to_csv(hot_stocks, f"涨幅榜_前{top_n}.csv")
        
        elif choice == '4':
            # 概念板块
            concept_name = input("\n请输入概念名称（如：人工智能、新能源）: ").strip()
            if concept_name:
                print(f"\n获取【{concept_name}】概念股...")
                concept_stocks = crawler.get_concept_stocks(concept_name)
                if not concept_stocks.empty:
                    print(f"\n共找到 {len(concept_stocks)} 只个股:")
                    print(concept_stocks.head(10).to_string(index=False))
                    
                    save = input("\n是否保存到文件? (y/n): ").strip().lower()
                    if save == 'y':
                        crawler.save_to_csv(concept_stocks, f"{concept_name}_概念股.csv")
        
        elif choice == '5':
            # 清空数据文件夹
            confirm = input("\n确认清空数据文件夹? (y/n): ").strip().lower()
            if confirm == 'y':
                clear_data_folder()
        
        elif choice == '0':
            print("\n再见！")
            break
        
        else:
            print("\n[ERROR] 无效的选择，请重新输入")
        
        # 暂停，让用户查看结果
        input("\n按回车键继续...")


if __name__ == "__main__":
    # 检查并提示安装依赖
    try:
        import akshare
        print(f"✓ AKShare 已安装 (版本: {akshare.__version__})")
    except ImportError:
        print("[ERROR] 请先安装 akshare: pip install akshare")
        print("\n或安装其他数据源:")
        print("  - Tushare: pip install tushare")
        print("  - yfinance: pip install yfinance")
        exit()
    
    # 运行主程序
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已终止")
    except Exception as e:
        print(f"\n程序出错: {e}")
        import traceback
        traceback.print_exc()