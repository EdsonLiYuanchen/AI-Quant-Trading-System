"""
数据库配置文件
包含MySQL连接参数和数据库配置
"""

# MySQL数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,  # 您的MySQL端口
    'user': 'root',
    'password': '703911',  # 您的MySQL密码
    'database': 'quantitative_trading',
    'charset': 'utf8mb4'
}

# 数据库表配置
TABLE_CONFIG = {
    # 股票基本信息表
    'stocks_basic': {
        'name': 'stocks_basic',
        'description': '股票基本信息表',
        'columns': [
            'id INT AUTO_INCREMENT PRIMARY KEY',
            'ts_code VARCHAR(20) UNIQUE NOT NULL COMMENT \'TS代码\'',
            'symbol VARCHAR(20) NOT NULL COMMENT \'股票代码\'',
            'name VARCHAR(100) NOT NULL COMMENT \'股票名称\'',
            'area VARCHAR(50) COMMENT \'所在地域\'',
            'industry VARCHAR(100) COMMENT \'所属行业\'',
            'market VARCHAR(20) COMMENT \'市场类型\'',
            'list_date DATE COMMENT \'上市日期\'',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'
        ]
    },
    
    # 日线行情数据表
    'daily_quotes': {
        'name': 'daily_quotes',
        'description': '日线行情数据表',
        'columns': [
            'id INT AUTO_INCREMENT PRIMARY KEY',
            'ts_code VARCHAR(20) NOT NULL COMMENT \'TS代码\'',
            'trade_date DATE NOT NULL COMMENT \'交易日期\'',
            'open DECIMAL(10,4) COMMENT \'开盘价\'',
            'high DECIMAL(10,4) COMMENT \'最高价\'',
            'low DECIMAL(10,4) COMMENT \'最低价\'',
            'close DECIMAL(10,4) COMMENT \'收盘价\'',
            'pre_close DECIMAL(10,4) COMMENT \'昨收价\'',
            'change DECIMAL(10,4) COMMENT \'涨跌额\'',
            'pct_chg DECIMAL(10,4) COMMENT \'涨跌幅\'',
            'vol DECIMAL(15,2) COMMENT \'成交量\'',
            'amount DECIMAL(15,2) COMMENT \'成交额\'',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'UNIQUE KEY unique_stock_date (ts_code, trade_date)'
        ]
    },
    
    # 财务数据表
    'financial_data': {
        'name': 'financial_data',
        'description': '财务数据表',
        'columns': [
            'id INT AUTO_INCREMENT PRIMARY KEY',
            'ts_code VARCHAR(20) NOT NULL COMMENT \'TS代码\'',
            'end_date DATE NOT NULL COMMENT \'报告期\'',
            'report_type VARCHAR(10) COMMENT \'报告类型\'',
            'total_revenue DECIMAL(20,2) COMMENT \'营业总收入\'',
            'net_profit DECIMAL(20,2) COMMENT \'净利润\'',
            'total_assets DECIMAL(20,2) COMMENT \'总资产\'',
            'total_liab DECIMAL(20,2) COMMENT \'总负债\'',
            'eps DECIMAL(10,4) COMMENT \'每股收益\'',
            'bps DECIMAL(10,4) COMMENT \'每股净资产\'',
            'roe DECIMAL(10,4) COMMENT \'净资产收益率\'',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'UNIQUE KEY unique_financial (ts_code, end_date, report_type)'
        ]
    },
    
    # 技术指标表
    'technical_indicators': {
        'name': 'technical_indicators',
        'description': '技术指标表',
        'columns': [
            'id INT AUTO_INCREMENT PRIMARY KEY',
            'ts_code VARCHAR(20) NOT NULL COMMENT \'TS代码\'',
            'trade_date DATE NOT NULL COMMENT \'交易日期\'',
            'ma5 DECIMAL(10,4) COMMENT \'5日均线\'',
            'ma10 DECIMAL(10,4) COMMENT \'10日均线\'',
            'ma20 DECIMAL(10,4) COMMENT \'20日均线\'',
            'ma60 DECIMAL(10,4) COMMENT \'60日均线\'',
            'rsi DECIMAL(10,4) COMMENT \'RSI指标\'',
            'macd DECIMAL(10,4) COMMENT \'MACD\'',
            'macd_signal DECIMAL(10,4) COMMENT \'MACD信号线\'',
            'macd_hist DECIMAL(10,4) COMMENT \'MACD柱状图\'',
            'kdj_k DECIMAL(10,4) COMMENT \'KDJ-K值\'',
            'kdj_d DECIMAL(10,4) COMMENT \'KDJ-D值\'',
            'kdj_j DECIMAL(10,4) COMMENT \'KDJ-J值\'',
            'boll_upper DECIMAL(10,4) COMMENT \'布林线上轨\'',
            'boll_middle DECIMAL(10,4) COMMENT \'布林线中轨\'',
            'boll_lower DECIMAL(10,4) COMMENT \'布林线下轨\'',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'UNIQUE KEY unique_technical (ts_code, trade_date)'
        ]
    },
    
    # 交易记录表
    'trading_records': {
        'name': 'trading_records',
        'description': '交易记录表',
        'columns': [
            'id INT AUTO_INCREMENT PRIMARY KEY',
            'strategy_name VARCHAR(100) NOT NULL COMMENT \'策略名称\'',
            'ts_code VARCHAR(20) NOT NULL COMMENT \'股票代码\'',
            'trade_date DATE NOT NULL COMMENT \'交易日期\'',
            'trade_type ENUM(\'BUY\', \'SELL\') NOT NULL COMMENT \'交易类型\'',
            'price DECIMAL(10,4) NOT NULL COMMENT \'交易价格\'',
            'volume INT NOT NULL COMMENT \'交易数量\'',
            'amount DECIMAL(15,2) NOT NULL COMMENT \'交易金额\'',
            'commission DECIMAL(10,4) COMMENT \'手续费\'',
            'profit_loss DECIMAL(15,2) COMMENT \'盈亏金额\'',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        ]
    }
}

# 数据同步配置
SYNC_CONFIG = {
    'batch_size': 100,  # 批量处理大小
    'delay_between_requests': 0.5,  # 请求间隔(秒)
    'max_retries': 3,  # 最大重试次数
    'retry_delay': 2  # 重试间隔(秒)
}

# 技术指标计算配置
TECHNICAL_CONFIG = {
    'ma_periods': [5, 10, 20, 60],  # 均线周期
    'rsi_period': 14,  # RSI周期
    'macd_fast': 12,  # MACD快线
    'macd_slow': 26,  # MACD慢线
    'macd_signal': 9,  # MACD信号线
    'boll_period': 20,  # 布林线周期
    'boll_std': 2  # 布林线标准差
}

def get_connection_string():
    """获取数据库连接字符串"""
    return f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

def test_connection():
    """测试数据库连接"""
    import mysql.connector
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"[OK] MySQL版本: {version}")
        
        cursor.execute("SHOW DATABASES LIKE 'quantitative_trading'")
        if cursor.fetchone():
            print("[OK] quantitative_trading数据库存在")
        else:
            print("[WARN] quantitative_trading数据库不存在")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] 数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    print("[TOOL] 数据库配置测试")
    print(f"[STAT] 主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"🗄️  数据库: {DB_CONFIG['database']}")
    print(f"[USER] 用户: {DB_CONFIG['user']}")
    print("\n正在测试连接...")
    test_connection()