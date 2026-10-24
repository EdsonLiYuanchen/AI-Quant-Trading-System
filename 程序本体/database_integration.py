"""
数据库集成模块
将数据爬取、分析、交易等功能与数据库集成
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
import logging
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def save_analysis_to_database(db_manager, analysis_type, result_data, stock_code=None, csv_file_path=None):
    """
    保存分析结果到数据库
    :param db_manager: 数据库管理器实例
    :param analysis_type: 分析类型
    :param result_data: 分析结果数据
    :param stock_code: 股票代码（可选）
    :param csv_file_path: CSV文件路径（可选）
    """
    if not db_manager:
        logger.warning("[WARN] 数据库管理器未初始化，跳过保存")
        return False
    
    try:
        # 检查是否支持保存分析结果
        if hasattr(db_manager, 'save_analysis_result'):
            return db_manager.save_analysis_result(analysis_type, result_data, stock_code, csv_file_path)
        else:
            logger.warning("[WARN] 数据库管理器不支持保存分析结果功能")
            return False
    except Exception as e:
        logger.error(f"[ERROR] 保存分析结果失败: {e}")
        return False


def sync_financial_data_to_database(db_manager, crawler, stock_codes, start_date=None, end_date=None):
    """
    同步金融数据到数据库
    :param db_manager: 数据库管理器实例
    :param crawler: 数据爬虫实例
    :param stock_codes: 股票代码列表
    :param start_date: 开始日期
    :param end_date: 结束日期
    """
    if not db_manager or not crawler:
        logger.error("[ERROR] 数据库管理器或爬虫未初始化")
        return False
    
    success_count = 0
    total_count = len(stock_codes)
    
    for stock_code in stock_codes:
        try:
            logger.info(f"[SYNC] 同步股票数据: {stock_code}")
            
            # 获取股票数据
            df = crawler.get_stock_daily(stock_code, start_date, end_date)
            
            if df.empty:
                logger.warning(f"[WARN] 股票 {stock_code} 数据为空，跳过")
                continue
            
            # 格式化数据
            if hasattr(crawler, '_format_data_for_database'):
                formatted_df = crawler._format_data_for_database(df, stock_code, 'daily_quotes')
            else:
                formatted_df = format_data_for_database(df, stock_code, 'daily_quotes')
            
            # 保存到数据库
            if hasattr(db_manager, 'insert_daily_quotes'):
                success = db_manager.insert_daily_quotes(formatted_df)
                if success:
                    success_count += 1
                    logger.info(f"[OK] 股票 {stock_code} 数据同步成功")
            
        except Exception as e:
            logger.error(f"[ERROR] 同步股票 {stock_code} 数据失败: {e}")
    
    logger.info(f"[OK] 数据同步完成: {success_count}/{total_count} 只股票成功")
    return success_count > 0


def format_data_for_database(df, stock_code, data_type):
    """
    格式化数据以适应数据库表结构
    :param df: 原始数据
    :param stock_code: 股票代码
    :param data_type: 数据类型
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


def export_analysis_to_csv_and_database(analyzer, db_manager, output_dir):
    """
    导出分析结果到CSV并保存到数据库
    :param analyzer: 分析器实例
    :param db_manager: 数据库管理器实例
    :param output_dir: 输出目录
    """
    if not analyzer or not db_manager:
        logger.error("[ERROR] 分析器或数据库管理器未初始化")
        return False
    
    try:
        # 分析所有文件
        results = analyzer.analyze_all_files()
        
        if not results:
            logger.warning("[WARN] 没有分析结果可导出")
            return False
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        success_count = 0
        
        for filename, analysis in results.items():
            try:
                # 生成CSV文件
                csv_file_path = os.path.join(output_dir, f"analysis_{filename.replace('.', '_')}.csv")
                
                # 将分析结果转换为DataFrame
                analysis_data = []
                
                # 基础信息
                basic_info = analysis.get('basic_info', {})
                analysis_data.append({
                    'category': 'basic_info',
                    'key': '总行数',
                    'value': basic_info.get('总行数', '')
                })
                analysis_data.append({
                    'category': 'basic_info',
                    'key': '总列数',
                    'value': basic_info.get('总列数', '')
                })
                
                # 统计信息
                stats = analysis.get('statistical_summary', {})
                if '数值列' in stats:
                    for col_name, col_stats in stats['数值列'].items():
                        for stat_name, stat_value in col_stats.items():
                            analysis_data.append({
                                'category': 'statistical_summary',
                                'key': f"{col_name}_{stat_name}",
                                'value': stat_value
                            })
                
                # 创建DataFrame并保存为CSV
                df = pd.DataFrame(analysis_data)
                df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
                
                # 保存到数据库
                save_analysis_to_database(
                    db_manager, 
                    'financial_analysis', 
                    analysis, 
                    None,  # 股票代码
                    csv_file_path
                )
                
                success_count += 1
                logger.info(f"[OK] 分析结果已导出: {filename}")
                
            except Exception as e:
                logger.error(f"[ERROR] 导出分析结果 {filename} 失败: {e}")
        
        logger.info(f"[OK] 分析结果导出完成: {success_count}/{len(results)} 个文件成功")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"[ERROR] 导出分析结果失败: {e}")
        return False


def get_database_connection_status(db_manager):
    """
    获取数据库连接状态
    :param db_manager: 数据库管理器实例
    :return: 连接状态字典
    """
    if not db_manager:
        return {
            'status': 'disconnected',
            'message': '数据库管理器未初始化'
        }
    
    try:
        # 检查连接是否有效
        if hasattr(db_manager, 'connection') and db_manager.connection:
            db_manager.cursor.execute("SELECT 1")
            return {
                'status': 'connected',
                'message': '数据库连接正常'
            }
        else:
            return {
                'status': 'disconnected',
                'message': '数据库连接未建立'
            }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'数据库连接错误: {e}'
        }


def backup_database_tables(db_manager, backup_dir):
    """
    备份数据库表到CSV文件
    :param db_manager: 数据库管理器实例
    :param backup_dir: 备份目录
    """
    if not db_manager:
        logger.error("[ERROR] 数据库管理器未初始化")
        return False
    
    try:
        # 创建备份目录
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # 获取所有表名
        db_manager.cursor.execute("SHOW TABLES")
        tables = [table['Tables_in_quantitative_trading'] for table in db_manager.cursor.fetchall()]
        
        success_count = 0
        
        for table in tables:
            try:
                # 查询表数据
                db_manager.cursor.execute(f"SELECT * FROM {table}")
                result = db_manager.cursor.fetchall()
                
                if result:
                    df = pd.DataFrame(result)
                    backup_file = os.path.join(backup_dir, f"{table}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                    df.to_csv(backup_file, index=False, encoding='utf-8-sig')
                    logger.info(f"[OK] 表 {table} 备份成功: {backup_file}")
                    success_count += 1
                else:
                    logger.warning(f"[WARN] 表 {table} 为空，跳过备份")
                    
            except Exception as e:
                logger.error(f"[ERROR] 备份表 {table} 失败: {e}")
        
        logger.info(f"[OK] 数据库备份完成: {success_count}/{len(tables)} 个表成功")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"[ERROR] 数据库备份失败: {e}")
        return False


# 使用示例
def test_database_integration():
    """测试数据库集成功能"""
    try:
        from enhanced_database_manager import EnhancedDatabaseManager
        from 爬取金融数据 import FinancialDataCrawler
        
        # 初始化数据库管理器
        db = EnhancedDatabaseManager()
        
        # 初始化数据爬虫
        crawler = FinancialDataCrawler(use_database=True)
        
        # 测试数据库连接状态
        status = get_database_connection_status(db)
        print(f"[STAT] 数据库状态: {status}")
        
        # 测试数据同步
        stock_codes = ['000001', '000002']
        success = sync_financial_data_to_database(db, crawler, stock_codes)
        print(f"[IN] 数据同步结果: {'成功' if success else '失败'}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        return False


if __name__ == "__main__":
    test_database_integration()