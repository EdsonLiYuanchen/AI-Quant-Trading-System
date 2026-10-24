"""
金融数据集成器
将爬取的金融数据集成到MySQL数据库中
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak
import tushare as ts
import yfinance as yf
import time
import logging
from database_manager import DatabaseManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FinancialDataIntegrator:
    """金融数据集成器"""
    
    def __init__(self):
        """初始化"""
        self.db = DatabaseManager()
        
    def get_stock_list(self, market='沪深A股'):
        """获取股票列表"""
        try:
            if market == '沪深A股':
                stock_list = ak.stock_info_a_code_name()
                # 转换为标准格式
                stock_list['ts_code'] = stock_list['code'] + '.SH'
                stock_list.loc[stock_list['code'].str.startswith('0') | stock_list['code'].str.startswith('3'), 'ts_code'] = stock_list['code'] + '.SZ'
                stock_list['symbol'] = stock_list['code']
                stock_list['name'] = stock_list['name']
                stock_list['market'] = 'A股'
                
                return stock_list[['ts_code', 'symbol', 'name', 'market']]
            
            elif market == '港股':
                stock_list = ak.stock_hk_spot_em()
                stock_list['ts_code'] = stock_list['代码'] + '.HK'
                stock_list['symbol'] = stock_list['代码']
                stock_list['name'] = stock_list['名称']
                stock_list['market'] = '港股'
                
                return stock_list[['ts_code', 'symbol', 'name', 'market']]
            
            else:
                logger.warning(f"[WARN] 不支持的股票市场: {market}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"[ERROR] 获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def sync_stock_basic_info(self, market='沪深A股'):
        """同步股票基本信息到数据库"""
        try:
            stock_list = self.get_stock_list(market)
            
            if not stock_list.empty:
                success = self.db.insert_stock_basic(stock_list)
                if success:
                    logger.info(f"[OK] 成功同步 {len(stock_list)} 条{market}股票基本信息")
                else:
                    logger.error(f"[ERROR] 同步{market}股票基本信息失败")
                return success
            else:
                logger.warning(f"[WARN] 未获取到{market}股票列表")
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] 同步股票基本信息失败: {e}")
            return False
    
    def get_daily_quotes(self, ts_code: str, start_date: str, end_date: str):
        """获取日线行情数据"""
        try:
            # 根据代码判断数据源
            if ts_code.endswith('.SH') or ts_code.endswith('.SZ'):
                # A股数据
                symbol = ts_code.replace('.SH', '').replace('.SZ', '')
                
                # 使用akshare获取数据
                stock_data = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                               start_date=start_date.replace('-', ''), 
                                               end_date=end_date.replace('-', ''), 
                                               adjust="qfq")
                
                if not stock_data.empty:
                    stock_data['ts_code'] = ts_code
                    stock_data['trade_date'] = pd.to_datetime(stock_data['日期']).dt.strftime('%Y-%m-%d')
                    stock_data['open'] = stock_data['开盘']
                    stock_data['high'] = stock_data['最高']
                    stock_data['low'] = stock_data['最低']
                    stock_data['close'] = stock_data['收盘']
                    stock_data['vol'] = stock_data['成交量']
                    stock_data['amount'] = stock_data['成交额']
                    stock_data['pct_chg'] = stock_data['涨跌幅']
                    
                    # 计算涨跌额
                    stock_data['price_change'] = stock_data['close'].diff()
                    stock_data['pre_close'] = stock_data['close'].shift(1)
                    
                    return stock_data[['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 
                                     'pre_close', 'price_change', 'pct_chg', 'vol', 'amount']]
            
            elif ts_code.endswith('.HK'):
                # 港股数据
                symbol = ts_code.replace('.HK', '')
                
                # 使用akshare获取港股数据
                stock_data = ak.stock_hk_hist(symbol=symbol, period="daily", 
                                             start_date=start_date.replace('-', ''), 
                                             end_date=end_date.replace('-', ''), 
                                             adjust="qfq")
                
                if not stock_data.empty:
                    stock_data['ts_code'] = ts_code
                    stock_data['trade_date'] = pd.to_datetime(stock_data['日期']).dt.strftime('%Y-%m-%d')
                    stock_data['open'] = stock_data['开盘']
                    stock_data['high'] = stock_data['最高']
                    stock_data['low'] = stock_data['最低']
                    stock_data['close'] = stock_data['收盘']
                    stock_data['vol'] = stock_data['成交量']
                    stock_data['amount'] = stock_data['成交额']
                    
                    # 计算涨跌幅
                    stock_data['pct_chg'] = stock_data['close'].pct_change() * 100
                    stock_data['price_change'] = stock_data['close'].diff()
                    stock_data['pre_close'] = stock_data['close'].shift(1)
                    
                    return stock_data[['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 
                                     'pre_close', 'price_change', 'pct_chg', 'vol', 'amount']]
            
            else:
                logger.warning(f"[WARN] 不支持的股票代码格式: {ts_code}")
                
        except Exception as e:
            logger.error(f"[ERROR] 获取 {ts_code} 行情数据失败: {e}")
        
        return pd.DataFrame()
    
    def sync_daily_quotes(self, ts_codes: list, start_date: str, end_date: str):
        """同步日线行情数据到数据库"""
        total_synced = 0
        
        for ts_code in ts_codes:
            try:
                logger.info(f"[SYNC] 正在同步 {ts_code} 的行情数据...")
                
                quotes_data = self.get_daily_quotes(ts_code, start_date, end_date)
                
                if not quotes_data.empty:
                    success = self.db.insert_daily_quotes(quotes_data)
                    if success:
                        total_synced += len(quotes_data)
                        logger.info(f"[OK] 成功同步 {ts_code} 的 {len(quotes_data)} 条行情数据")
                    else:
                        logger.error(f"[ERROR] 同步 {ts_code} 行情数据失败")
                else:
                    logger.warning(f"[WARN] 未获取到 {ts_code} 的行情数据")
                
                # 避免请求过于频繁
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"[ERROR] 同步 {ts_code} 行情数据时出错: {e}")
        
        logger.info(f"[STAT] 总共同步了 {total_synced} 条行情数据")
        return total_synced
    
    def calculate_all_technical_indicators(self, ts_codes: list):
        """为所有股票计算技术指标"""
        total_calculated = 0
        
        for ts_code in ts_codes:
            try:
                logger.info(f"[UP] 正在计算 {ts_code} 的技术指标...")
                
                success = self.db.calculate_technical_indicators(ts_code)
                if success:
                    total_calculated += 1
                    logger.info(f"[OK] 成功计算 {ts_code} 的技术指标")
                else:
                    logger.error(f"[ERROR] 计算 {ts_code} 技术指标失败")
                
            except Exception as e:
                logger.error(f"[ERROR] 计算 {ts_code} 技术指标时出错: {e}")
        
        logger.info(f"[STAT] 总共为 {total_calculated} 只股票计算了技术指标")
        return total_calculated
    
    def get_portfolio_analysis(self, portfolio: dict):
        """获取投资组合分析"""
        try:
            analysis_results = {}
            
            for ts_code, weight in portfolio.items():
                # 获取最近一年的数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                
                stock_data = self.db.get_stock_data(ts_code, start_date, end_date)
                
                if not stock_data.empty:
                    # 计算收益率
                    returns = stock_data['close'].pct_change().dropna()
                    
                    analysis_results[ts_code] = {
                        'weight': weight,
                        'total_return': (stock_data['close'].iloc[-1] / stock_data['close'].iloc[0] - 1) * 100,
                        'annual_return': returns.mean() * 252 * 100,
                        'volatility': returns.std() * np.sqrt(252) * 100,
                        'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0,
                        'max_drawdown': self.calculate_max_drawdown(stock_data['close'])
                    }
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"[ERROR] 投资组合分析失败: {e}")
            return {}
    
    def calculate_max_drawdown(self, prices):
        """计算最大回撤"""
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak
        return drawdown.min() * 100
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()


# 使用示例
def test_data_integration():
    """测试数据集成功能"""
    try:
        integrator = FinancialDataIntegrator()
        
        # 1. 同步股票基本信息
        print("[SYNC] 正在同步股票基本信息...")
        integrator.sync_stock_basic_info('沪深A股')
        
        # 2. 同步部分股票的行情数据
        print("[SYNC] 正在同步行情数据...")
        test_codes = ['000001.SZ', '600000.SH', '00700.HK']
        start_date = '2024-01-01'
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        integrator.sync_daily_quotes(test_codes, start_date, end_date)
        
        # 3. 计算技术指标
        print("[UP] 正在计算技术指标...")
        integrator.calculate_all_technical_indicators(test_codes)
        
        # 4. 投资组合分析
        print("[STAT] 进行投资组合分析...")
        portfolio = {'000001.SZ': 0.4, '600000.SH': 0.4, '00700.HK': 0.2}
        analysis = integrator.get_portfolio_analysis(portfolio)
        
        for stock, metrics in analysis.items():
            print(f"\n[UP] {stock} 分析结果:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value:.2f}")
        
        integrator.close()
        print("\n[OK] 数据集成测试完成!")
        
    except Exception as e:
        print(f"[ERROR] 数据集成测试失败: {e}")


if __name__ == "__main__":
    test_data_integration()