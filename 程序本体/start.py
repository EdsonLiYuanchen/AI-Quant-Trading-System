# -*- coding: utf-8 -*-
"""
AI量化交易系统 - 智能启动器
自动检测数据库环境并启动应用
- 如果有MySQL且可连接，使用MySQL
- 否则自动使用SQLite（免安装）
"""
import sys
import os
import json
import subprocess
import platform
from pathlib import Path

print("=== AI Trading System Launcher ===")
print(f"Python版本: {sys.version}")
print(f"工作目录: {os.getcwd()}")

# 尝试导入SQLite数据库管理器
def try_sqlite_db():
    """尝试使用SQLite数据库"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from database_manager_sqlite import SQLiteDatabaseManager
        db = SQLiteDatabaseManager()
        print("[OK] 使用SQLite数据库")
        return db
    except Exception as e:
        print(f"[WARN] SQLite初始化失败: {e}")
        return None

def try_mysql_db():
    """尝试使用MySQL数据库"""
    try:
        import mysql.connector
        # 读取数据库配置
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'database': 'quantitative_trading'
            }
        
        if not config.get('password'):
            print("[WARN] MySQL密码未配置，将使用SQLite")
            return None
        
        conn = mysql.connector.connect(**config)
        print(f"[OK] 使用MySQL数据库: {config['host']}:{config['port']}/{config['database']}")
        return conn
    except ImportError:
        print("[INFO] mysql.connector未安装，将使用SQLite")
        return None
    except Exception as e:
        print(f"[WARN] MySQL连接失败: {e}，将使用SQLite")
        return None

# 尝试连接数据库
print("\n[检查数据库环境]")
db = try_mysql_db()
if db is None:
    print("[提示] 未检测到可用的MySQL，将使用内置SQLite数据库")
    db = try_sqlite_db()

if db is None:
    print("[ERROR] 无法初始化数据库")
    input("按Enter退出...")
    sys.exit(1)

# 关闭数据库连接（如果是MySQL）
if db and hasattr(db, 'close'):
    db.close()

try:
    print("\n路径添加成功")
    print("正在导入AI量化交易系统GUI...")
    
    # 添加当前目录到路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # 导入主模块
    from AI量化交易系统GUI import main
    print("模块导入成功")
    
    print("正在启动主程序...")
    main()
    
except Exception as e:
    print(f"\n错误类型: {type(e).__name__}")
    print(f"错误信息: {e}")
    import traceback
    traceback.print_exc()
    input("\n按Enter退出...")
