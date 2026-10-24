"""
增强版数据库管理器
支持数据同步、CSV导入导出、数据分析存储等功能
"""

import mysql.connector
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
import os
import glob
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedDatabaseManager:
    """增强版MySQL数据库管理器"""
    
    def __init__(self, host='localhost', port=3306, user='root', password='703911', database='quantitative_trading'):
        """
        初始化数据库连接
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.cursor = None
        
        # 新增表结构：分析结果表
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
            """,
            'analysis_results': """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    analysis_type VARCHAR(50) NOT NULL COMMENT '分析类型',
                    stock_code VARCHAR(20) COMMENT '股票代码',
                    analysis_date DATE NOT NULL COMMENT '分析日期',
                    result_json JSON COMMENT '分析结果(JSON格式)',
                    csv_file_path VARCHAR(500) COMMENT 'CSV文件路径',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_analysis_type (analysis_type),
                    INDEX idx_stock_code (stock_code)
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
            logger.info(f"[OK] 成功连接到数据库: {self.database} (端口: {self.port})")
            return True
        except mysql.connector.Error as e:
            logger.error(f"[ERROR] 数据库连接失败: {e}")
            return False
    
    def create_tables(self):
        """创建数据表"""
        if not self.connection:
            logger.error("[ERROR] 数据库未连接")
            return False
        
        try:
            for table_name, create_sql in self.table_definitions.items():
                self.cursor.execute(create_sql)
                logger.info(f"[OK] 表 {table_name} 创建/检查完成")
            
            self.connection.commit()
            logger.info("[OK] 所有数据表创建完成")
            return True
        except mysql.connector.Error as e:
            logger.error(f"[ERROR] 创建表失败: {e}")
            return False
    
    def sync_csv_to_database(self, csv_directory):
        """
        将CSV文件夹中的数据同步到数据库
        :param csv_directory: CSV文件夹路径
        """
        if not os.path.exists(csv_directory):
            logger.error(f"[ERROR] 文件夹不存在: {csv_directory}")
            return False
        
        csv_files = glob.glob(os.path.join(csv_directory, "*.csv"))
        if not csv_files:
            logger.warning(f"[WARN] 文件夹中没有CSV文件: {csv_directory}")
            return False
        
        success_count = 0
        total_count = len(csv_files)
        
        for csv_file in csv_files:
            filename = os.path.basename(csv_file)
            logger.info(f"[SYNC] 处理文件: {filename}")
            
            try:
                # 读取CSV文件
                df = pd.read_csv(csv_file, encoding='utf-8')
                
                # 根据文件名判断数据类型
                if '日线' in filename or '_daily' in filename:
                    # 日线数据
                    stock_code = filename.split('_')[0]
                    formatted_df = self._format_daily_data(df, stock_code)
                    if self.insert_daily_quotes(formatted_df):
                        success_count += 1
                elif '财务' in filename or '_financial' in filename:
                    # 财务数据
                    stock_code = filename.split('_')[0]
                    formatted_df = self._format_financial_data(df, stock_code)
                    if self.insert_financial_data(formatted_df):
                        success_count += 1
                else:
                    # 通用数据
                    logger.info(f"[NOTE] 通用数据文件: {filename}")
                    
            except Exception as e:
                logger.error(f"[ERROR] 处理文件 {filename} 失败: {e}")
        
        logger.info(f"[OK] 同步完成: {success_count}/{total_count} 个文件成功")
        return success_count > 0
    
    def export_database_to_csv(self, output_directory, table_name=None):
        """
        将数据库表导出为CSV文件
        :param output_directory: 输出目录
        :param table_name: 表名（可选，为空则导出所有表）
        """
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        
        tables_to_export = [table_name] if table_name else self.table_definitions.keys()
        success_count = 0
        
        for table in tables_to_export:
            try:
                # 查询表数据
                self.cursor.execute(f"SELECT * FROM {table}")
                result = self.cursor.fetchall()
                
                if result:
                    df = pd.DataFrame(result)
                    output_file = os.path.join(output_directory, f"{table}.csv")
                    df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    logger.info(f"[OK] 导出表 {table} 到 {output_file}")
                    success_count += 1
                else:
                    logger.warning(f"[WARN] 表 {table} 为空，跳过导出")
                    
            except Exception as e:
                logger.error(f"[ERROR] 导出表 {table} 失败: {e}")
        
        logger.info(f"[OK] 导出完成: {success_count} 个表成功")
        return success_count > 0
    
    def save_analysis_result(self, analysis_type, result_data, stock_code=None, csv_file_path=None):
        """
        保存分析结果到数据库
        :param analysis_type: 分析类型
        :param result_data: 分析结果数据
        :param stock_code: 股票代码（可选）
        :param csv_file_path: CSV文件路径（可选）
        """
        sql = """
            INSERT INTO analysis_results 
            (analysis_type, stock_code, analysis_date, result_json, csv_file_path)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            # 将结果转换为JSON格式
            result_json = json.dumps(result_data, ensure_ascii=False, indent=2)
            
            self.cursor.execute(sql, (
                analysis_type,
                stock_code,
                datetime.now().strftime('%Y-%m-%d'),
                result_json,
                csv_file_path
            ))
            
            self.connection.commit()
            logger.info(f"[OK] 分析结果已保存到数据库 (类型: {analysis_type})")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 保存分析结果失败: {e}")
            return False
    
    def get_database_stats(self):
        """获取数据库统计信息"""
        stats = {}
        
        try:
            for table in self.table_definitions.keys():
                self.cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                result = self.cursor.fetchone()
                stats[table] = result['count'] if result else 0
            
            return stats
        except Exception as e:
            logger.error(f"[ERROR] 获取数据库统计失败: {e}")
            return {}
    
    def _format_daily_data(self, df, stock_code):
        """格式化日线数据"""
        df_formatted = df.copy()
        df_formatted['ts_code'] = stock_code
        
        # 重命名列
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
        
        df_formatted = df_formatted.rename(columns=column_mapping)
        
        # 格式化日期
        if 'trade_date' in df_formatted.columns:
            df_formatted['trade_date'] = pd.to_datetime(df_formatted['trade_date']).dt.strftime('%Y-%m-%d')
        
        # 添加缺失字段
        if 'pre_close' not in df_formatted.columns:
            df_formatted['pre_close'] = df_formatted['close'].shift(1)
        if 'price_change' not in df_formatted.columns:
            df_formatted['price_change'] = df_formatted['close'] - df_formatted['pre_close']
        
        return df_formatted
    
    def _format_financial_data(self, df, stock_code):
        """格式化财务数据"""
        df_formatted = df.copy()
        df_formatted['ts_code'] = stock_code
        
        # 这里可以根据实际的财务数据格式进行调整
        # 示例格式化逻辑
        column_mapping = {
            '报告期': 'end_date',
            '营业收入': 'total_revenue',
            '净利润': 'net_profit',
            '总资产': 'total_assets',
            '总负债': 'total_liab'
        }
        
        df_formatted = df_formatted.rename(columns=column_mapping)
        
        return df_formatted
    
    # 原有的数据插入方法（保持兼容）
    def insert_daily_quotes(self, quotes_data):
        """插入日线行情数据"""
        if quotes_data.empty:
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
                    row.get('price_change'), row.get('pct_chg'),
                    row.get('vol'), row.get('amount')
                )
                self.cursor.execute(sql, values)
            
            self.connection.commit()
            logger.info(f"[OK] 成功插入/更新 {len(quotes_data)} 条行情数据")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 插入行情数据失败: {e}")
            return False
    
    def insert_financial_data(self, financial_data):
        """插入财务数据"""
        if financial_data.empty:
            return False
        
        sql = """
            INSERT INTO financial_data 
            (ts_code, end_date, report_type, total_revenue, net_profit, 
             total_assets, total_liab, eps, bps, roe) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                total_revenue=VALUES(total_revenue), net_profit=VALUES(net_profit),
                total_assets=VALUES(total_assets), total_liab=VALUES(total_liab),
                eps=VALUES(eps), bps=VALUES(bps), roe=VALUES(roe)
        """
        
        try:
            for _, row in financial_data.iterrows():
                values = (
                    row.get('ts_code'), row.get('end_date'), row.get('report_type'),
                    row.get('total_revenue'), row.get('net_profit'),
                    row.get('total_assets'), row.get('total_liab'),
                    row.get('eps'), row.get('bps'), row.get('roe')
                )
                self.cursor.execute(sql, values)
            
            self.connection.commit()
            logger.info(f"[OK] 成功插入/更新 {len(financial_data)} 条财务数据")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 插入财务数据失败: {e}")
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
def test_enhanced_database():
    """测试增强版数据库功能"""
    try:
        db = EnhancedDatabaseManager()
        
        # 显示数据库表
        db.cursor.execute("SHOW TABLES")
        tables = db.cursor.fetchall()
        print("[LIST] 数据库中的表:")
        for table in tables:
            print(f"  - {table['Tables_in_quantitative_trading']}")
        
        # 显示统计信息
        stats = db.get_database_stats()
        print("\n[STAT] 数据库统计:")
        for table, count in stats.items():
            print(f"  - {table}: {count} 条记录")
        
        return True
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        return False


if __name__ == "__main__":
    test_enhanced_database()