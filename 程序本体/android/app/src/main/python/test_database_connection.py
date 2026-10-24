"""
数据库连接测试脚本
测试MySQL数据库连接和配置
"""

import mysql.connector
from database_manager import DatabaseManager
from database_config import DB_CONFIG, test_connection

def test_mysql_connection():
    """测试MySQL基础连接"""
    print("[TOOL] 测试MySQL数据库连接")
    print("=" * 50)
    
    try:
        # 使用mysql.connector直接测试
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 测试版本
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"[OK] MySQL服务器版本: {version}")
        
        # 测试数据库存在性
        cursor.execute("SHOW DATABASES LIKE 'quantitative_trading'")
        db_exists = cursor.fetchone()
        
        if db_exists:
            print("[OK] quantitative_trading数据库存在")
            
            # 切换到目标数据库
            cursor.execute("USE quantitative_trading")
            
            # 显示表
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            if tables:
                print("[LIST] 数据库中的表:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("[WARN]  数据库中没有表")
        else:
            print("[ERROR] quantitative_trading数据库不存在")
            print("[IDEA] 请运行 mysql_setup.sql 创建数据库")
        
        cursor.close()
        conn.close()
        print("[OK] MySQL基础连接测试通过")
        return True
        
    except mysql.connector.Error as e:
        print(f"[ERROR] MySQL连接失败: {e}")
        print("[IDEA] 请检查:")
        print("  1. MySQL服务是否启动")
        print("  2. 用户名和密码是否正确")
        print("  3. 端口号是否正确")
        return False

def test_database_manager():
    """测试DatabaseManager类"""
    print("\n[TOOL] 测试DatabaseManager类")
    print("=" * 50)
    
    try:
        # 使用DatabaseManager测试
        db = DatabaseManager()
        
        if db.connection:
            print("[OK] DatabaseManager连接成功")
            
            # 显示表结构
            db.cursor.execute("SHOW TABLES")
            tables = db.cursor.fetchall()
            
            if tables:
                print("[LIST] DatabaseManager管理的表:")
                for table in tables:
                    table_name = table['Tables_in_quantitative_trading']
                    print(f"\n[STAT] 表: {table_name}")
                    
                    # 显示表结构
                    db.cursor.execute(f"DESCRIBE {table_name}")
                    columns = db.cursor.fetchall()
                    
                    for col in columns:
                        print(f"  {col['Field']} ({col['Type']}) - {col.get('Comment', '')}")
            
            db.close()
            print("\n[OK] DatabaseManager测试通过")
            return True
        else:
            print("[ERROR] DatabaseManager连接失败")
            return False
            
    except Exception as e:
        print(f"[ERROR] DatabaseManager测试失败: {e}")
        return False

def test_data_operations():
    """测试数据操作功能"""
    print("\n[TOOL] 测试数据操作功能")
    print("=" * 50)
    
    try:
        db = DatabaseManager()
        
        # 测试插入股票基本信息
        test_stock_data = [
            ('000001.SZ', '000001', '平安银行', '广东', '银行', 'A股', '1991-04-03'),
            ('600000.SH', '600000', '浦发银行', '上海', '银行', 'A股', '1999-11-10'),
            ('00700.HK', '00700', '腾讯控股', '香港', '互联网', '港股', '2004-06-16')
        ]
        
        # 创建测试DataFrame
        import pandas as pd
        df = pd.DataFrame(test_stock_data, columns=['ts_code', 'symbol', 'name', 'area', 'industry', 'market', 'list_date'])
        
        # 插入数据
        success = db.insert_stock_basic(df)
        
        if success:
            print("[OK] 股票基本信息插入测试通过")
            
            # 查询验证
            db.cursor.execute("SELECT COUNT(*) as count FROM stocks_basic")
            count = db.cursor.fetchone()['count']
            print(f"[STAT] 当前股票数量: {count}")
        else:
            print("[ERROR] 股票基本信息插入失败")
        
        db.close()
        return success
        
    except Exception as e:
        print(f"[ERROR] 数据操作测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("[RUN] AI量化交易系统 - 数据库连接测试")
    print("=" * 60)
    
    # 显示配置信息
    print("[STAT] 当前配置:")
    print(f"  主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  数据库: {DB_CONFIG['database']}")
    print(f"  用户: {DB_CONFIG['user']}")
    print(f"  密码: {'*' * len(DB_CONFIG['password'])}")
    
    # 执行测试
    tests = [
        ("MySQL基础连接", test_mysql_connection),
        ("DatabaseManager", test_database_manager),
        ("数据操作功能", test_data_operations)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[ERROR] {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 60)
    print("[LIST] 测试结果汇总:")
    
    passed = 0
    for test_name, result in results:
        status = "[OK] 通过" if result else "[ERROR] 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n[TGT] 总体结果: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！数据库配置正确。")
        print("\n[IDEA] 下一步:")
        print("  1. 运行 financial_data_integrator.py 同步金融数据")
        print("  2. 运行 融合版AI量化交易系统.py 启动主程序")
    else:
        print("\n[WARN]  部分测试失败，请检查数据库配置。")

if __name__ == "__main__":
    main()