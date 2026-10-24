"""
SQLite数据库管理器 - 便携版
无需安装MySQL，数据存储在本地SQLite文件中
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SQLiteDatabaseManager:
    """SQLite数据库管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化SQLite数据库
        
        Args:
            db_path: 数据库文件路径，默认为 app_data_dir/quantitative_trading.db
        """
        if db_path is None:
            # 默认路径：应用目录下的 data 文件夹
            app_dir = os.path.dirname(os.path.abspath(__file__))
            db_dir = os.path.join(app_dir, "data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "quantitative_trading.db")
        
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self.create_tables()
    
    def connect(self):
        """连接到SQLite数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.connection.cursor()
            logger.info(f"[OK] 成功连接到SQLite数据库: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 数据库连接失败: {e}")
            return False
    
    def create_tables(self):
        """创建数据表"""
        self.connect()
        
        tables_sql = {
            'stocks_basic': """
                CREATE TABLE IF NOT EXISTS stocks_basic (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT,
                    area TEXT,
                    industry TEXT,
                    market TEXT,
                    list_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            
            'daily_quotes': """
                CREATE TABLE IF NOT EXISTS daily_quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    pre_close REAL,
                    change REAL,
                    pct_chg REAL,
                    vol REAL,
                    amount REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ts_code, trade_date)
                )
            """,
            
            'financial_data': """
                CREATE TABLE IF NOT EXISTS financial_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    end_date DATE NOT NULL,
                    report_type TEXT,
                    total_revenue REAL,
                    net_profit REAL,
                    total_assets REAL,
                    total_liab REAL,
                    eps REAL,
                    bps REAL,
                    roe REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ts_code, end_date, report_type)
                )
            """,
            
            'technical_indicators': """
                CREATE TABLE IF NOT EXISTS technical_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    ma5 REAL,
                    ma10 REAL,
                    ma20 REAL,
                    ma60 REAL,
                    rsi REAL,
                    macd REAL,
                    macd_signal REAL,
                    macd_hist REAL,
                    kdj_k REAL,
                    kdj_d REAL,
                    kdj_j REAL,
                    boll_upper REAL,
                    boll_middle REAL,
                    boll_lower REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ts_code, trade_date)
                )
            """,
            
            'trading_records': """
                CREATE TABLE IF NOT EXISTS trading_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    ts_code TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    trade_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    commission REAL,
                    profit_loss REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            
            'analysis_results': """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    analysis_date DATE NOT NULL,
                    strategy TEXT,
                    signal TEXT,
                    confidence REAL,
                    prediction REAL,
                    actual_return REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
        
        for table_name, create_sql in tables_sql.items():
            try:
                self.cursor.execute(create_sql)
                self.connection.commit()
                logger.info(f"[OK] 表 {table_name} 创建/检查完成")
            except Exception as e:
                logger.error(f"[ERROR] 创建表 {table_name} 失败: {e}")
    
    def execute(self, sql: str, params: tuple = None):
        """执行SQL语句"""
        if not self.connection:
            self.connect()
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            self.connection.commit()
            return self.cursor
        except Exception as e:
            logger.error(f"执行SQL失败: {e}")
            raise
    
    def query(self, sql: str, params: tuple = None) -> List[dict]:
        """查询数据"""
        if not self.connection:
            self.connect()
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            columns = [desc[0] for desc in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return []
    
    def dataframe_to_table(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append'):
        """将DataFrame写入数据库表"""
        if not self.connection:
            self.connect()
        try:
            df.to_sql(table_name, self.connection, if_exists=if_exists, index=False)
            self.connection.commit()
            logger.info(f"[OK] 写入 {len(df)} 条记录到表 {table_name}")
            return True
        except Exception as e:
            logger.error(f"写入失败: {e}")
            return False
    
    def get_database_stats(self) -> dict:
        """获取数据库统计信息"""
        stats = {}
        try:
            if not self.connection:
                self.connect()
            
            # 获取所有表
            tables = self.query("SELECT name FROM sqlite_master WHERE type='table'")
            stats['tables'] = len(tables)
            stats['table_names'] = [t['name'] for t in tables]
            
            # 获取每个表的记录数
            for table in tables:
                count = self.query(f"SELECT COUNT(*) as cnt FROM [{table['name']}]")
                stats[table['name']] = count[0]['cnt'] if count else 0
            
            # 获取数据库文件大小
            if os.path.exists(self.db_path):
                stats['file_size_mb'] = round(os.path.getsize(self.db_path) / 1024 / 1024, 2)
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
        
        return stats
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("[OK] 数据库连接已关闭")


def main():
    """测试函数"""
    db = SQLiteDatabaseManager()
    stats = db.get_database_stats()
    print(f"数据库路径: {db.db_path}")
    print(f"数据库大小: {stats.get('file_size_mb', 0)} MB")
    print(f"表数量: {stats['tables']}")
    for table, count in stats.items():
        if isinstance(count, int) and table not in ['tables', 'table_names', 'file_size_mb']:
            print(f"  {table}: {count} 条记录")
    db.close()


if __name__ == "__main__":
    main()
