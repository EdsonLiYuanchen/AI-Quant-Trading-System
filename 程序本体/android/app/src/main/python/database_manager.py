"""
MySQL数据库管理器
用于连接quantitative_trading数据库，存储和管理金融数据
配置信息：localhost:3306, root/703911
"""

import mysql.connector
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseManager:
    """MySQL数据库管理器"""
    
    def __init__(self, host='localhost', port=3306, user='root', password='703911', database='quantitative_trading'):
        """
        初始化数据库连接
        
        Args:
            host: MySQL服务器地址
            port: MySQL端口 (默认: 3306)
            user: 用户名 (默认: root)
            password: 密码 (默认: 703911)
            database: 数据库名称 (默认: quantitative_trading)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.cursor = None
        
        # 数据库表结构定义
        self.table_definitions = {
            'stocks_basic': """
                CREATE TABLE IF NOT EXISTS stocks_basic (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ts_code VARCHAR(20) UNIQUE NOT NULL COMMENT 'TS代码',
                    symbol VARCHAR(20) NOT NULL COMMENT '股票代码',
                    name VARCHAR(100) NOT NULL COMMENT '股票名称',
                    area VARCHAR(50) COMMENT '所在地域',
                    industry VARCHAR(100) COMMENT '所属行业',
                    market VARCHAR(20) COMMENT '市场类型',
                    list_date DATE COMMENT '上市日期',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """,
            'daily_quotes': """
                CREATE TABLE IF NOT EXISTS daily_quotes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ts_code VARCHAR(20) NOT NULL COMMENT 'TS代码',
                    trade_date DATE NOT NULL COMMENT '交易日期',
                    open DECIMAL(10,4) COMMENT '开盘价',
                    high DECIMAL(10,4) COMMENT '最高价',
                    low DECIMAL(10,4) COMMENT '最低价',
                    close DECIMAL(10,4) COMMENT '收盘价',
                    pre_close DECIMAL(10,4) COMMENT '昨收价',
                    price_change DECIMAL(10,4) COMMENT '涨跌额',
                    pct_chg DECIMAL(10,4) COMMENT '涨跌幅',
                    vol DECIMAL(15,2) COMMENT '成交量',
                    amount DECIMAL(15,2) COMMENT '成交额',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_stock_date (ts_code, trade_date)
                )
            """,
            'financial_data': """
                CREATE TABLE IF NOT EXISTS financial_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ts_code VARCHAR(20) NOT NULL COMMENT 'TS代码',
                    end_date DATE NOT NULL COMMENT '报告期',
                    report_type VARCHAR(10) COMMENT '报告类型',
                    total_revenue DECIMAL(20,2) COMMENT '营业总收入',
                    net_profit DECIMAL(20,2) COMMENT '净利润',
                    total_assets DECIMAL(20,2) COMMENT '总资产',
                    total_liab DECIMAL(20,2) COMMENT '总负债',
                    eps DECIMAL(10,4) COMMENT '每股收益',
                    bps DECIMAL(10,4) COMMENT '每股净资产',
                    roe DECIMAL(10,4) COMMENT '净资产收益率',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_financial (ts_code, end_date, report_type)
                )
            """,
            'technical_indicators': """
                CREATE TABLE IF NOT EXISTS technical_indicators (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ts_code VARCHAR(20) NOT NULL COMMENT 'TS代码',
                    trade_date DATE NOT NULL COMMENT '交易日期',
                    ma5 DECIMAL(10,4) COMMENT '5日均线',
                    ma10 DECIMAL(10,4) COMMENT '10日均线',
                    ma20 DECIMAL(10,4) COMMENT '20日均线',
                    ma60 DECIMAL(10,4) COMMENT '60日均线',
                    rsi DECIMAL(10,4) COMMENT 'RSI指标',
                    macd DECIMAL(10,4) COMMENT 'MACD',
                    macd_signal DECIMAL(10,4) COMMENT 'MACD信号线',
                    macd_hist DECIMAL(10,4) COMMENT 'MACD柱状图',
                    kdj_k DECIMAL(10,4) COMMENT 'KDJ-K值',
                    kdj_d DECIMAL(10,4) COMMENT 'KDJ-D值',
                    kdj_j DECIMAL(10,4) COMMENT 'KDJ-J值',
                    boll_upper DECIMAL(10,4) COMMENT '布林线上轨',
                    boll_middle DECIMAL(10,4) COMMENT '布林线中轨',
                    boll_lower DECIMAL(10,4) COMMENT '布林线下轨',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_technical (ts_code, trade_date)
                )
            """,
            'trading_records': """
                CREATE TABLE IF NOT EXISTS trading_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
                    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
                    trade_date DATE NOT NULL COMMENT '交易日期',
                    trade_type ENUM('BUY', 'SELL') NOT NULL COMMENT '交易类型',
                    price DECIMAL(10,4) NOT NULL COMMENT '交易价格',
                    volume INT NOT NULL COMMENT '交易数量',
                    amount DECIMAL(15,2) NOT NULL COMMENT '交易金额',
                    commission DECIMAL(10,4) COMMENT '手续费',
                    profit_loss DECIMAL(15,2) COMMENT '盈亏金额',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
        
        self.connect()
        self.create_tables()
    
    def connect(self):
        """连接到MySQL数据库"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.connection.cursor(dictionary=True)
            logger.info("[OK] 成功连接到数据库: %s (端口: %d)" % (self.database, self.port))
            return True
        except mysql.connector.Error as e:
            logger.error("[ERROR] 数据库连接失败: %s" % str(e))
            return False
    
    def create_tables(self):
        """创建数据表"""
        if not self.connection:
            logger.error("[ERROR] 数据库未连接")
            return False
        
        try:
            for table_name, create_sql in self.table_definitions.items():
                self.cursor.execute(create_sql)
                logger.info("[OK] 表 %s 创建/检查完成" % table_name)
            
            self.connection.commit()
            logger.info("[OK] 所有数据表创建完成")
            return True
        except mysql.connector.Error as e:
            logger.error("[ERROR] 创建表失败: %s" % str(e))
            return False
    
    def insert_stock_basic(self, stock_data: pd.DataFrame):
        """插入股票基本信息"""
        if stock_data.empty:
            logger.warning("[WARN] 股票基本信息为空")
            return False
        
        sql = """
            INSERT INTO stocks_basic 
            (ts_code, symbol, name, area, industry, market, list_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                name=VALUES(name), area=VALUES(area), industry=VALUES(industry),
                market=VALUES(market), list_date=VALUES(list_date)
        """
        
        try:
            for _, row in stock_data.iterrows():
                values = (
                    row.get('ts_code'), row.get('symbol'), row.get('name'),
                    row.get('area'), row.get('industry'), row.get('market'),
                    row.get('list_date')
                )
                self.cursor.execute(sql, values)
            
            self.connection.commit()
            logger.info(f"[OK] 成功插入/更新 {len(stock_data)} 条股票基本信息")
            return True
        except mysql.connector.Error as e:
            logger.error(f"[ERROR] 插入股票基本信息失败: {e}")
            return False
    
    def insert_daily_quotes(self, quotes_data: pd.DataFrame):
        """插入日线行情数据"""
        if quotes_data.empty:
            logger.warning("[WARN] 行情数据为空")
            return False
        
        sql = """
            INSERT INTO daily_quotes 
            (ts_code, trade_date, open, high, low, close, pre_close, 
             price_change, pct_chg, vol, amount) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                open=VALUES(open), high=VALUES(high), low=VALUES(low),
                close=VALUES(close), pre_close=VALUES(pre_close),
                price_change=VALUES(price_change), pct_chg=VALUES(pct_chg),
                vol=VALUES(vol), amount=VALUES(amount)
        """
        
        try:
            for _, row in quotes_data.iterrows():
                values = (
                    row.get('ts_code'), row.get('trade_date'),
                    row.get('open'), row.get('high'), row.get('low'),
                    row.get('close'), row.get('pre_close'),
                    row.get('change'), row.get('pct_chg'),
                    row.get('vol'), row.get('amount')
                )
                self.cursor.execute(sql, values)
            
            self.connection.commit()
            logger.info(f"[OK] 成功插入/更新 {len(quotes_data)} 条行情数据")
            return True
        except mysql.connector.Error as e:
            logger.error(f"[ERROR] 插入行情数据失败: {e}")
            return False
    
    def get_stock_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取指定股票的历史数据"""
        sql = """
            SELECT trade_date, open, high, low, close, vol, amount, pct_chg
            FROM daily_quotes 
            WHERE ts_code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date
        """
        
        try:
            self.cursor.execute(sql, (ts_code, start_date, end_date))
            result = self.cursor.fetchall()
            
            if result:
                df = pd.DataFrame(result)
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df.set_index('trade_date', inplace=True)
                logger.info(f"[STAT] 获取到 {ts_code} 的 {len(df)} 条数据")
                return df
            else:
                logger.warning(f"[WARN] 未找到 {ts_code} 在 {start_date} 到 {end_date} 的数据")
                return pd.DataFrame()
        except mysql.connector.Error as e:
            logger.error(f"[ERROR] 查询股票数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, ts_code: str, window: int = 20):
        """计算技术指标并存储"""
        # 获取股票数据
        df = self.get_stock_data(ts_code, '2000-01-01', datetime.now().strftime('%Y-%m-%d'))
        
        if df.empty:
            return False
        
        # 计算技术指标
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 插入技术指标数据
        sql = """
            INSERT INTO technical_indicators 
            (ts_code, trade_date, ma5, ma10, ma20, ma60, rsi) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                ma5=VALUES(ma5), ma10=VALUES(ma10), ma20=VALUES(ma20),
                ma60=VALUES(ma60), rsi=VALUES(rsi)
        """
        
        try:
            for date, row in df.iterrows():
                if pd.notna(row['ma20']):  # 确保有足够的数据计算指标
                    values = (
                        ts_code, date.strftime('%Y-%m-%d'),
                        row['ma5'], row['ma10'], row['ma20'], row['ma60'], row['rsi']
                    )
                    self.cursor.execute(sql, values)
            
            self.connection.commit()
            logger.info(f"[OK] 成功计算并存储 {ts_code} 的技术指标")
            return True
        except mysql.connector.Error as e:
            logger.error(f"[ERROR] 计算技术指标失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("[CONN] 数据库连接已关闭")
    
    def __del__(self):
        """析构函数"""
        self.close()


# 使用示例
def test_database_connection():
    """测试数据库连接"""
    try:
        db = DatabaseManager()
        
        # 测试查询
        db.cursor.execute("SHOW TABLES")
        tables = db.cursor.fetchall()
        print("[LIST] 数据库中的表:")
        for table in tables:
            print(f"  - {table['Tables_in_quantitative_trading']}")
        
        return True
    except Exception as e:
        print(f"[ERROR] 数据库连接测试失败: {e}")
        return False


if __name__ == "__main__":
    test_database_connection()