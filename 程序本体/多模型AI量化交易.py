"""
多模型AI量化交易系统
支持多种机器学习模型选择和对比
"""

import sys
import quant_metrics as _qm
import os
sys.path.append(os.path.dirname(__file__))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import warnings
import json
import pickle
import os
import sys
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, AdaBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
try:
    import msvcrt  # Windows 专用（命令行按键检测），非 Windows 平台不可用
    HAS_MSVCRT = True
except ImportError:
    msvcrt = None
    HAS_MSVCRT = False
warnings.filterwarnings('ignore')

try:
    from 爬取金融数据 import FinancialDataCrawler
except:
    print("请确保 爬取金融数据.py 在同一目录")
    sys.exit(1)


# ===================== AI模型配置 =====================
AI_MODELS = {
    '1': {
        'name': '随机森林 (Random Forest)',
        'model': RandomForestClassifier,
        'params': {'n_estimators': 100, 'random_state': 42, 'max_depth': 10},
        'description': '集成学习，多棵决策树投票，适合金融数据',
        'speed': '快',
        'accuracy': '高'
    },
    '2': {
        'name': '梯度提升树 (Gradient Boosting)',
        'model': GradientBoostingClassifier,
        'params': {'n_estimators': 100, 'random_state': 42, 'learning_rate': 0.1},
        'description': '强力集成学习，精度高但训练较慢',
        'speed': '中',
        'accuracy': '很高'
    },
    '3': {
        'name': '神经网络 (Neural Network)',
        'model': MLPClassifier,
        'params': {'hidden_layer_sizes': (100, 50), 'random_state': 42, 'max_iter': 500},
        'description': '多层感知机，能学习复杂非线性关系',
        'speed': '中',
        'accuracy': '高'
    },
    '4': {
        'name': '逻辑回归 (Logistic Regression)',
        'model': LogisticRegression,
        'params': {'random_state': 42, 'max_iter': 1000},
        'description': '经典线性模型，速度快但表达能力有限',
        'speed': '很快',
        'accuracy': '中'
    },
    '5': {
        'name': '支持向量机 (SVM)',
        'model': SVC,
        'params': {'kernel': 'rbf', 'random_state': 42, 'probability': True},
        'description': '强大的分类器，适合小数据集',
        'speed': '慢',
        'accuracy': '高'
    },
    '6': {
        'name': 'AdaBoost 提升算法',
        'model': AdaBoostClassifier,
        'params': {'n_estimators': 100, 'random_state': 42, 'learning_rate': 1.0},
        'description': '自适应提升，不断强化错误样本学习',
        'speed': '快',
        'accuracy': '高'
    },
    '7': {
        'name': '决策树 (Decision Tree)',
        'model': DecisionTreeClassifier,
        'params': {'random_state': 42, 'max_depth': 10},
        'description': '单棵决策树，简单直观但容易过拟合',
        'speed': '很快',
        'accuracy': '中'
    },
    '8': {
        'name': '朴素贝叶斯 (Naive Bayes)',
        'model': GaussianNB,
        'params': {},
        'description': '基于概率的经典算法，速度快',
        'speed': '很快',
        'accuracy': '中'
    }
}


class AIStrategyOptimizer:
    """AI策略优化器 - 支持多种模型"""
    
    def __init__(self, model_type='1', name=None):
        self.model_type = model_type
        self.model_info = AI_MODELS.get(model_type, AI_MODELS['1'])
        self.name = name or self.model_info['name']
        
        # 创建模型实例
        ModelClass = self.model_info['model']
        self.model = ModelClass(**self.model_info['params'])
        
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # 可学习的参数范围
        self.param_ranges = {
            'ma_short': [3, 5, 7, 10],
            'ma_long': [10, 15, 20, 30],
            'rsi_oversold': [20, 25, 30, 35],
            'rsi_overbought': [65, 70, 75, 80],
            'bb_std': [1.5, 2.0, 2.5, 3.0],
        }
        
        # 当前最优参数
        self.best_params = {
            'ma_short': 5,
            'ma_long': 20,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_std': 2.0,
            'volume_threshold': 1.2,
        }
        
        # 学习历史
        self.learning_history = []
        self.performance_history = []
        
    def extract_features(self, df, index):
        """提取特征用于机器学习"""
        if index < 60:
            return None
            
        current = df.iloc[index]
        
        features = []
        
        # 基础价格特征
        features.append(current['收盘'])
        
        # 移动平均线特征（如果存在）
        ma_features = []
        for ma_col in ['MA5', 'MA10', 'MA20', 'MA60']:
            if ma_col in df.columns and pd.notna(current[ma_col]) and current[ma_col] > 0:
                ma_features.append(current['收盘'] / current[ma_col])
            else:
                ma_features.append(1.0)
        features.extend(ma_features)
        
        # 技术指标特征（如果存在）
        tech_indicators = []
        for indicator in ['RSI', 'DIF', 'DEA', 'MACD']:
            if indicator in df.columns and pd.notna(current[indicator]):
                tech_indicators.append(current[indicator])
            else:
                tech_indicators.append(0.0)
        features.extend(tech_indicators)
        
        # 布林带特征（如果存在）
        if 'BB_UPPER' in df.columns and 'BB_LOWER' in df.columns:
            if pd.notna(current['BB_UPPER']) and pd.notna(current['BB_LOWER']):
                bb_width = (current['BB_UPPER'] - current['BB_LOWER']) / current['收盘']
                bb_position = (current['收盘'] - current['BB_LOWER']) / (current['BB_UPPER'] - current['BB_LOWER'])
            else:
                bb_width = 0
                bb_position = 0.5
        else:
            bb_width = 0
            bb_position = 0.5
        features.extend([bb_width, bb_position])
        
        # 成交量特征（如果存在）
        if 'VOL_MA5' in df.columns and pd.notna(current['VOL_MA5']) and current['VOL_MA5'] > 0:
            vol_ratio = current['成交量'] / current['VOL_MA5']
        else:
            vol_ratio = 1
        features.append(vol_ratio)
        
        # 趋势特征
        if index >= 5:
            price_change_5d = (current['收盘'] - df.iloc[index-5]['收盘']) / df.iloc[index-5]['收盘'] * 100
            price_change_20d = (current['收盘'] - df.iloc[index-20]['收盘']) / df.iloc[index-20]['收盘'] * 100 if index >= 20 else 0
        else:
            price_change_5d = 0
            price_change_20d = 0
        features.extend([price_change_5d, price_change_20d])
        
        return np.array(features)
    
    def train_model(self, df):
        """训练机器学习模型"""
        print(f"\n[BOT] [{self.name}] 正在学习历史数据...")
        start_time = time.time()
        
        # 先计算技术指标
        try:
            strategy = AITradingStrategy(self.model_type, use_ai=False)
            df_with_indicators = strategy.calculate_indicators(df.copy())
            
            # 验证指标计算是否成功
            required_indicators = ['MA5', 'MA20', 'RSI', 'MACD']
            missing_indicators = [ind for ind in required_indicators if ind not in df_with_indicators.columns]
            if missing_indicators:
                print(f"[WARN]  技术指标计算不完整，缺少: {missing_indicators}")
                # 使用基本特征进行训练
                df_with_indicators = df.copy()
        except Exception as e:
            print(f"[ERROR] 技术指标计算失败，使用基本特征: {e}")
            df_with_indicators = df.copy()
        
        X = []
        y = []
        
        # 为每个时间点提取特征和标签
        for i in range(60, len(df_with_indicators) - 5):
            features = self.extract_features(df_with_indicators, i)
            if features is None:
                continue
                
            # 标签：未来5天是否上涨
            future_return = (df_with_indicators.iloc[i+5]['收盘'] - df_with_indicators.iloc[i]['收盘']) / df_with_indicators.iloc[i]['收盘']
            label = 1 if future_return > 0.02 else 0
            
            X.append(features)
            y.append(label)
        
        if len(X) < 50:
            print("[WARN]  数据不足，无法训练模型")
            return False
        
        X = np.array(X)
        y = np.array(y)
        
        # 标准化特征
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练模型
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        # 计算训练准确率
        train_score = self.model.score(X_scaled, y)
        training_time = time.time() - start_time
        
        print(f"✓ [{self.name}] 学习完成！")
        print(f"  训练准确率: {train_score*100:.2f}%")
        print(f"  训练时间: {training_time:.2f}秒")
        
        return True
    
    def predict_signal(self, df, index):
        """使用AI预测交易信号"""
        if not self.is_trained:
            return 0
            
        features = self.extract_features(df, index)
        if features is None:
            return 0
            
        # 预测
        features_scaled = self.scaler.transform([features])
        prediction = self.model.predict(features_scaled)[0]
        
        # 获取预测概率（某些模型不支持）
        try:
            proba = self.model.predict_proba(features_scaled)[0]
            confidence = max(proba)
            
            # 只有较高置信度才返回信号（阈值过高会导致回测永不触发买入）
            if confidence > 0.55:
                return 1 if prediction == 1 else -1
        except:
            # 不支持概率预测的模型直接返回预测结果
            return 1 if prediction == 1 else -1
        
        return 0
    
    def optimize_parameters(self, backtest_results):
        """根据回测结果优化参数"""
        print(f"\n[TOOL] [{self.name}] 正在优化策略参数...")
        
        # 记录本次性能
        self.performance_history.append(backtest_results)
        
        # 简单的参数优化
        if backtest_results['returns'] > 10:
            print("✓ 策略表现良好，参数保持")
        elif backtest_results['returns'] < 0:
            print("[WARN]  策略表现不佳，调整参数...")
            if backtest_results['win_rate'] < 0.4:
                self.best_params['rsi_oversold'] = max(20, self.best_params['rsi_oversold'] - 2)
                self.best_params['rsi_overbought'] = min(80, self.best_params['rsi_overbought'] + 2)
            
            if backtest_results['total_trades'] < 5:
                self.best_params['ma_short'] = max(3, self.best_params['ma_short'] - 1)
        
        self.learning_history.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'params': self.best_params.copy(),
            'performance': backtest_results['returns']
        })
        
        print(f"✓ 参数优化完成")
        print(f"   当前最优参数: {self.best_params}")
    
    def save_model(self, filepath=None):
        """保存模型"""
        if filepath is None:
            filepath = f'ai_model_{self.model_type}.pkl'
        
        model_data = {
            'model': self.model,
            'model_type': self.model_type,
            'model_info': self.model_info,
            'scaler': self.scaler,
            'is_trained': self.is_trained,
            'best_params': self.best_params,
            'learning_history': self.learning_history,
            'performance_history': self.performance_history
        }
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        print(f"✓ [{self.name}] 模型已保存到: {filepath}")
    
    def load_model(self, filepath=None):
        """加载模型"""
        if filepath is None:
            filepath = f'ai_model_{self.model_type}.pkl'
        
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            self.model = model_data['model']
            self.model_type = model_data.get('model_type', self.model_type)
            self.model_info = model_data.get('model_info', self.model_info)
            self.scaler = model_data['scaler']
            self.is_trained = model_data['is_trained']
            self.best_params = model_data['best_params']
            self.learning_history = model_data.get('learning_history', [])
            self.performance_history = model_data.get('performance_history', [])
            print(f"✓ [{self.name}] 模型已加载: {filepath}")
            return True
        except FileNotFoundError:
            print(f"[WARN]  未找到已保存的模型: {filepath}")
            return False


class AITradingStrategy:
    """AI增强交易策略"""
    
    def __init__(self, model_type='1', use_ai=True, initial_cash=100000.0):
        self.positions = {}
        self.cash = float(initial_cash)
        self.initial_cash = self.cash
        self.trade_history = []
        self.use_ai = use_ai
        # 交易成本模型（借鉴主流量化框架：佣金 + 滑点）
        self.commission_rate = _qm.DEFAULT_COMMISSION_RATE
        self.slippage_rate = _qm.DEFAULT_SLIPPAGE_RATE
        self.total_cost = 0.0        # 累计交易成本（元）
        self.total_turnover = 0.0    # 累计成交额（元）
        self.equity_curve = [float(initial_cash)]  # 逐日权益，供绩效指标

        
        # AI优化器
        self.ai_optimizer = AIStrategyOptimizer(model_type=model_type)
        self.name = f"AI策略 ({self.ai_optimizer.name})"
        
    def calculate_indicators(self, df):
        """计算技术指标"""
        if df.empty or len(df) < 30:
            return df
        
        params = self.ai_optimizer.best_params
        
        # 移动平均线
        try:
            df['MA5'] = df['收盘'].rolling(window=params['ma_short']).mean()
            df['MA10'] = df['收盘'].rolling(window=10).mean()
            df['MA20'] = df['收盘'].rolling(window=params['ma_long']).mean()
            df['MA60'] = df['收盘'].rolling(window=60).mean()
        except Exception as e:
            print(f"[ERROR] 移动平均线计算失败: {e}")
            # 使用默认窗口计算
            df['MA5'] = df['收盘'].rolling(window=5).mean()
            df['MA10'] = df['收盘'].rolling(window=10).mean()
            df['MA20'] = df['收盘'].rolling(window=20).mean()
            df['MA60'] = df['收盘'].rolling(window=60).mean()
        
        # MACD
        df['EMA12'] = df['收盘'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['收盘'].ewm(span=26, adjust=False).mean()
        df['DIF'] = df['EMA12'] - df['EMA26']
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2
        
        # RSI
        delta = df['收盘'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 布林带
        df['BB_MIDDLE'] = df['收盘'].rolling(window=20).mean()
        std = df['收盘'].rolling(window=20).std()
        df['BB_UPPER'] = df['BB_MIDDLE'] + params['bb_std'] * std
        df['BB_LOWER'] = df['BB_MIDDLE'] - params['bb_std'] * std
        
        # 成交量均线
        df['VOL_MA5'] = df['成交量'].rolling(window=5).mean()
        df['VOL_MA10'] = df['成交量'].rolling(window=10).mean()
        
        df['涨跌幅'] = df['收盘'].pct_change() * 100
        
        return df
    
    def buy_signal(self, df, index):
        """AI增强买入信号"""
        if index < 60:
            return False
        
        current = df.iloc[index]
        previous = df.iloc[index - 1]
        params = self.ai_optimizer.best_params
        
        # AI预测信号
        ai_signal = 0
        if self.use_ai and self.ai_optimizer.is_trained:
            ai_signal = self.ai_optimizer.predict_signal(df, index)
        
        # 传统技术指标信号
        signals = []
        
        # 1. 均线信号
        if pd.notna(current['MA5']) and pd.notna(current['MA20']):
            if current['MA5'] > current['MA20'] and previous['MA5'] <= previous['MA20']:
                signals.append(1)
        
        # 2. MACD信号
        if pd.notna(current['DIF']) and pd.notna(current['DEA']):
            if current['DIF'] > current['DEA'] and previous['DIF'] <= previous['DEA']:
                signals.append(1)
        
        # 3. RSI超卖
        if pd.notna(current['RSI']) and current['RSI'] < params['rsi_oversold']:
            signals.append(1)
        
        # 4. 布林带下轨
        if pd.notna(current['BB_LOWER']) and current['收盘'] < current['BB_LOWER']:
            signals.append(1)
        
        # 5. 成交量放大
        if pd.notna(current['VOL_MA5']) and current['成交量'] > current['VOL_MA5'] * params['volume_threshold']:
            signals.append(1)
        
        # 综合判断
        traditional_signal = sum(signals) >= 2
        
        # AI 与传统信号取或：AI 增强但不过度依赖单一通道，避免回测全程不交易
        if self.use_ai:
            return (ai_signal == 1) or traditional_signal
        return traditional_signal
    
    def sell_signal(self, df, index):
        """AI增强卖出信号"""
        if index < 60:
            return False
        
        current = df.iloc[index]
        previous = df.iloc[index - 1]
        params = self.ai_optimizer.best_params
        
        # AI预测信号
        ai_signal = 0
        if self.use_ai and self.ai_optimizer.is_trained:
            ai_signal = self.ai_optimizer.predict_signal(df, index)
        
        # 传统技术指标信号
        signals = []
        
        # 1. 均线死叉
        if pd.notna(current['MA5']) and pd.notna(current['MA20']):
            if current['MA5'] < current['MA20'] and previous['MA5'] >= previous['MA20']:
                signals.append(1)
        
        # 2. MACD死叉
        if pd.notna(current['DIF']) and pd.notna(current['DEA']):
            if current['DIF'] < current['DEA'] and previous['DIF'] >= previous['DEA']:
                signals.append(1)
        
        # 3. RSI超买
        if pd.notna(current['RSI']) and current['RSI'] > params['rsi_overbought']:
            signals.append(1)
        
        # 4. 布林带上轨
        if pd.notna(current['BB_UPPER']) and current['收盘'] > current['BB_UPPER']:
            signals.append(1)
        
        traditional_signal = sum(signals) >= 2
        
        # AI 与传统信号取或：保证回测有买卖动作，胜率/收益率才有意义
        if self.use_ai:
            return (ai_signal == -1) or traditional_signal
        return traditional_signal
    
    def execute_trade(self, stock_code, action, price, volume, date):
        """执行交易"""
        if action == 'buy':
            cost = price * volume * 100
            # 成本感知：滑点抬高买入价 + 佣金/印花税（单边）
            eff_price = _qm.apply_cost(price, 'buy', self.slippage_rate)
            turnover = eff_price * volume * 100
            fee = _qm.commission_cost(eff_price, volume, self.commission_rate, 0.0)
            if turnover + fee <= self.cash:
                self.cash -= (turnover + fee)
                self.positions[stock_code] = self.positions.get(stock_code, 0) + volume
                self.total_cost += fee
                self.total_turnover += turnover
                self.trade_history.append({
                    'date': date,
                    'action': 'buy',
                    'price': eff_price,
                    'volume': volume,
                    'stock': stock_code,
                    'fee': fee
                })
                self._record_equity(eff_price)
        elif action == 'sell':
            if stock_code in self.positions and self.positions[stock_code] >= volume:
            # 成本感知：滑点压低卖出价 + 佣金/印花税（单边）
                eff_price = _qm.apply_cost(price, 'sell', self.slippage_rate)
                turnover = eff_price * volume * 100
                fee = _qm.commission_cost(eff_price, volume, self.commission_rate, 0.0)
                self.cash += (turnover - fee)
                self.positions[stock_code] -= volume
                if self.positions[stock_code] == 0:
                    del self.positions[stock_code]
                self.total_cost += fee
                self.total_turnover += turnover
                self.trade_history.append({
                    'date': date,
                    'action': 'sell',
                    'price': eff_price,
                    'volume': volume,
                    'stock': stock_code,
                    'fee': fee
                })
                self._record_equity(eff_price)

    def _record_equity(self, ref_price=None):
        """在交易日追加一条权益值（现金 + 持仓按参考价估值），供 Sharpe/回撤等指标。"""
        value = self.cash
        if ref_price is not None:
            for code, vol in self.positions.items():
                value += ref_price * vol * 100
        self.equity_curve.append(value)



class MultiModelBacktester:
    """多模型回测器"""

    def __init__(self, model_type='1', use_ai=True, portfolio_manager=None, initial_cash=100000.0):
        self.use_ai = use_ai
        self.strategy = AITradingStrategy(model_type=model_type, use_ai=use_ai, initial_cash=initial_cash)
        self.crawler = FinancialDataCrawler()
        self.portfolio_manager = portfolio_manager  # 持仓管理器
    
    def run_backtest(self, stock_code, start_date, end_date):
        """运行回测"""
        print(f"\n{'='*70}")
        print(f"[BOT] [{self.strategy.ai_optimizer.name}] 量化交易回测")
        print(f"{'='*70}")
        print(f"股票代码: {stock_code}")
        print(f"AI模式: {'开启' if self.use_ai else '关闭'}")
        print(f"{'='*70}")
        
        # 获取数据
        df = self.crawler.get_stock_daily(stock_code, start_date, end_date)
        if df is None or df.empty:
            print("[ERROR] 无法获取股票数据")
            return None
        
        # 数据列名兼容性处理
        df = self._normalize_column_names(df)
        
        # 验证数据列名
        required_columns = ['日期', '收盘', '成交量']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"[ERROR] 数据缺少必要列: {missing_columns}")
            print(f"当前数据列名: {list(df.columns)}")
            return None
        
        # 检查数据量是否足够
        if len(df) < 60:
            print(f"[ERROR] 数据量不足，至少需要60条记录，当前只有{len(df)}条")
            return None
        
        # 第一步：AI学习
        if self.use_ai:
            print("\n[STAT] 阶段1: AI学习历史数据...")
            if not self.strategy.ai_optimizer.train_model(df):
                return None
        
        # 第二步：计算指标
        print("\n[UP] 阶段2: 计算技术指标...")
        try:
            df = self.strategy.calculate_indicators(df)
            # 验证指标计算是否成功
            required_indicators = ['MA5', 'MA20', 'RSI', 'MACD']
            missing_indicators = [ind for ind in required_indicators if ind not in df.columns]
            if missing_indicators:
                print(f"[WARN]  部分技术指标计算失败: {missing_indicators}")
        except Exception as e:
            print(f"[ERROR] 技术指标计算失败: {e}")
            return None
        
        # 第三步：执行策略
        print("\n[MONEY] 阶段3: 执行交易策略...")
        buy_count = 0
        sell_count = 0
        
        for i in range(60, len(df)):
            stock_code_clean = stock_code
            
            # 买入信号
            if self.strategy.buy_signal(df, i) and stock_code_clean not in self.strategy.positions:
                price = df.iloc[i]['收盘']
                volume = int((self.strategy.cash * 0.3) / (price * 100))
                if volume > 0:
                    self.strategy.execute_trade(stock_code_clean, 'buy', price, volume, df.iloc[i]['日期'])
                    buy_count += 1
                    print(f"  [UP] [买入] {df.iloc[i]['日期']} 价格: {price:.2f} 数量: {volume} 手")
            
            # 卖出信号
            elif self.strategy.sell_signal(df, i) and stock_code_clean in self.strategy.positions:
                price = df.iloc[i]['收盘']
                volume = self.strategy.positions[stock_code_clean]
                self.strategy.execute_trade(stock_code_clean, 'sell', price, volume, df.iloc[i]['日期'])
                sell_count += 1
                print(f"  [DOWN] [卖出] {df.iloc[i]['日期']} 价格: {price:.2f} 数量: {volume} 手")
        
        # 平仓
        if stock_code_clean in self.strategy.positions:
            final_price = df.iloc[-1]['收盘']
            volume = self.strategy.positions[stock_code_clean]
            self.strategy.execute_trade(stock_code_clean, 'sell', final_price, volume, df.iloc[-1]['日期'])
            print(f"  [LOCK] [平仓] {df.iloc[-1]['日期']} 价格: {final_price:.2f} 数量: {volume} 手")
        
        # 计算结果
        results = self.analyze_results(df, buy_count, sell_count)
        
        # AI学习
        if self.use_ai:
            print("\n[AI] 阶段4: AI学习回测结果...")
            self.strategy.ai_optimizer.optimize_parameters(results)
            self.strategy.ai_optimizer.save_model()
        
        return results
    
    def run_backtest_with_existing_data(self, stock_code):
        """使用现有数据文件进行回测"""
        print(f"\n{'='*70}")
        print(f"[BOT] [{self.strategy.ai_optimizer.name}] 使用现有数据文件回测")
        print(f"{'='*70}")
        print(f"股票代码: {stock_code}")
        print(f"AI模式: {'开启' if self.use_ai else '关闭'}")
        print(f"数据源: 本地数据文件")
        print(f"{'='*70}")
        
        # 查找匹配的数据文件
        data_file = self._find_matching_data_file(stock_code)
        if not data_file:
            print(f"[ERROR] 找不到股票 {stock_code} 的数据文件")
            print(f"请确保数据文件存在且文件名包含股票代码")
            return None
        
        print(f"📂 使用数据文件: {os.path.basename(data_file)}")
        
        # 使用查找的文件进行回测
        return self._run_backtest_from_file(stock_code, data_file)
    
    def run_backtest_with_specific_file(self, stock_code, file_path):
        """使用指定的数据文件进行回测"""
        print(f"\n{'='*70}")
        print(f"[BOT] [{self.strategy.ai_optimizer.name}] 使用指定数据文件回测")
        print(f"{'='*70}")
        print(f"股票代码: {stock_code}")
        print(f"AI模式: {'开启' if self.use_ai else '关闭'}")
        print(f"数据源: 用户选择文件")
        print(f"文件路径: {os.path.basename(file_path)}")
        print(f"{'='*70}")
        
        if not os.path.exists(file_path):
            print(f"[ERROR] 指定的数据文件不存在: {file_path}")
            return None
        
        print(f"📂 使用指定数据文件: {os.path.basename(file_path)}")
        
        # 使用指定的文件进行回测
        return self._run_backtest_from_file(stock_code, file_path)
    
    def _run_backtest_from_file(self, stock_code, file_path):
        """从指定文件运行回测（内部方法）"""
        # 读取数据文件
        try:
            df = pd.read_csv(file_path)
            print(f"[OK] 成功读取数据: {len(df)} 条记录")
            
            # 数据列名兼容性处理
            df = self._normalize_column_names(df)
            
            # 验证数据列名
            required_columns = ['日期', '收盘', '成交量']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"[ERROR] 数据缺少必要列: {missing_columns}")
                print(f"当前数据列名: {list(df.columns)}")
                return None
            
            # 检查数据量是否足够
            if len(df) < 60:
                print(f"[ERROR] 数据量不足，至少需要60条记录，当前只有{len(df)}条")
                return None
            
            # 显示数据时间范围
            if '日期' in df.columns:
                start_date = df['日期'].iloc[0] if hasattr(df['日期'].iloc[0], 'strftime') else df['日期'].iloc[0]
                end_date = df['日期'].iloc[-1] if hasattr(df['日期'].iloc[-1], 'strftime') else df['日期'].iloc[-1]
                print(f"📅 数据时间范围: {start_date} 至 {end_date}")
            
            # 执行回测（复用现有逻辑）
            # 第一步：AI学习
            if self.use_ai:
                print("\n[STAT] 阶段1: AI学习历史数据...")
                if not self.strategy.ai_optimizer.train_model(df):
                    return None
            
            # 第二步：计算指标
            print("\n[UP] 阶段2: 计算技术指标...")
            try:
                df = self.strategy.calculate_indicators(df)
                # 验证指标计算是否成功
                required_indicators = ['MA5', 'MA20', 'RSI', 'MACD']
                missing_indicators = [ind for ind in required_indicators if ind not in df.columns]
                if missing_indicators:
                    print(f"[WARN]  部分技术指标计算失败: {missing_indicators}")
            except Exception as e:
                print(f"[ERROR] 技术指标计算失败: {e}")
                return None
            
            # 第三步：执行策略
            print("\n[MONEY] 阶段3: 执行交易策略...")
            buy_count = 0
            sell_count = 0
            
            for i in range(60, len(df)):
                stock_code_clean = stock_code
                
                # 买入信号
                if self.strategy.buy_signal(df, i) and stock_code_clean not in self.strategy.positions:
                    price = df.iloc[i]['收盘']
                    volume = int((self.strategy.cash * 0.3) / (price * 100))
                    if volume <= 0 and self.strategy.cash >= price * 100:
                        volume = 1  # 高价股预算不足3成时，只要现金够1手也买1手
                    if volume > 0:
                        self.strategy.execute_trade(stock_code_clean, 'buy', price, volume, df.iloc[i]['日期'])
                        buy_count += 1
                        print(f"  [UP] [买入] {df.iloc[i]['日期']} 价格: {price:.2f} 数量: {volume} 手")
                
                # 卖出信号
                elif self.strategy.sell_signal(df, i) and stock_code_clean in self.strategy.positions:
                    price = df.iloc[i]['收盘']
                    volume = self.strategy.positions[stock_code_clean]
                    self.strategy.execute_trade(stock_code_clean, 'sell', price, volume, df.iloc[i]['日期'])
                    sell_count += 1
                    print(f"  [DOWN] [卖出] {df.iloc[i]['日期']} 价格: {price:.2f} 数量: {volume} 手")
            
            # 平仓
            if stock_code_clean in self.strategy.positions:
                final_price = df.iloc[-1]['收盘']
                volume = self.strategy.positions[stock_code_clean]
                self.strategy.execute_trade(stock_code_clean, 'sell', final_price, volume, df.iloc[-1]['日期'])
                print(f"  [LOCK] [平仓] {df.iloc[-1]['日期']} 价格: {final_price:.2f} 数量: {volume} 手")
            
            # 计算结果
            results = self.analyze_results(df, buy_count, sell_count)
            
            # AI学习
            if self.use_ai:
                print("\n[AI] 阶段4: AI学习回测结果...")
                self.strategy.ai_optimizer.optimize_parameters(results)
                self.strategy.ai_optimizer.save_model()
            
            return results
            
        except Exception as e:
            print(f"[ERROR] 读取数据文件失败: {e}")
            return None
    
    def _find_matching_data_file(self, stock_code):
        """查找匹配的数据文件"""
        import glob
        
        # 查找数据目录
        data_dirs = [
            os.path.join(os.path.dirname(__file__), "金融数据"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "金融数据"),
            os.path.join(os.path.dirname(__file__))
        ]
        
        # 可能的文件模式
        patterns = [
            f"*{stock_code}*.csv",
            f"{stock_code}*.csv",
            f"*{stock_code}*.xlsx",
            f"{stock_code}*.xlsx"
        ]
        
        for data_dir in data_dirs:
            if os.path.exists(data_dir):
                for pattern in patterns:
                    files = glob.glob(os.path.join(data_dir, pattern))
                    if files:
                        # 返回最新的文件
                        latest_file = max(files, key=os.path.getmtime)
                        return latest_file
        
        return None
    
    def _normalize_column_names(self, df):
        """标准化数据列名"""
        column_mapping = {
            'date': '日期',
            'close': '收盘',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'volume': '成交量',
            'amount': '成交额'
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        # 确保日期列是datetime类型
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'])
        
        return df
    
    def analyze_results(self, df, buy_count, sell_count):
        """分析回测结果"""
        final_value = self.strategy.cash
        returns = (final_value - self.strategy.initial_cash) / self.strategy.initial_cash * 100

        start_price = df.iloc[0]['收盘']
        end_price = df.iloc[-1]['收盘']
        buy_hold_return = (end_price - start_price) / start_price * 100

        # 计算胜率
        win_trades = 0
        total_trades = 0
        for i in range(0, len(self.strategy.trade_history), 2):
            if i + 1 < len(self.strategy.trade_history):
                buy_trade = self.strategy.trade_history[i]
                sell_trade = self.strategy.trade_history[i + 1]
                if sell_trade['price'] > buy_trade['price']:
                    win_trades += 1
                total_trades += 1

        win_rate = win_trades / total_trades if total_trades > 0 else 0

        # 打印结果
        print(f"\n{'='*70}")
        print(f"[STAT] [{self.strategy.ai_optimizer.name}] 回测结果")
        print(f"{'='*70}")
        print(f"交易次数: {len(self.strategy.trade_history)} (买{buy_count}/卖{sell_count})")
        print(f"胜率: {win_rate*100:.2f}% ({win_trades}/{total_trades})")
        print(f"初始资金: {self.strategy.initial_cash:,.2f} 元")
        print(f"最终资产: {final_value:,.2f} 元")
        print(f"总收益: {final_value - self.strategy.initial_cash:,.2f} 元")
        print(f"收益率: {returns:.2f}%")
        print(f"买入持有收益率: {buy_hold_return:.2f}%")
        print(f"超额收益: {returns - buy_hold_return:.2f}%")

        # 如果有持仓管理器,显示持仓对比
        if self.portfolio_manager:
            print(f"\n[WORK] 真实持仓对比:")
            print(f"{'-'*70}")
            portfolio_value = self.portfolio_manager.get_total_value()
            portfolio_profit = self.portfolio_manager.get_total_profit_loss()
            portfolio_profit_pct = self.portfolio_manager.get_total_profit_loss_pct()

            print(f"持仓资产: {portfolio_value:,.2f} 元")
            print(f"持仓盈亏: {portfolio_profit:+,.2f} 元 ({portfolio_profit_pct:+.2f}%)")

            # 根据回测结果生成AI交易建议
            if self.use_ai:
                latest_price = df.iloc[-1]['收盘']
                print(f"\n[BOT] AI交易建议:")
                print(f"{'-'*70}")

                # 对比回测收益和持仓收益
                if returns > 10:
                    print("[OK] 回测策略表现优秀(收益率>10%)")
                    if self.portfolio_manager.has_position(end_price.split('_')[0] if '_' in str(end_price) else ''):
                        signal, reason = self.portfolio_manager.get_ai_trading_signal(
                            end_price.split('_')[0] if '_' in str(end_price) else '',
                            1, latest_price
                        )
                        print(f"   策略信号: {signal} - {reason}")
                elif returns > 0:
                    print("[WARN]  回测策略表现一般(0-10%)")
                    print("   建议: 可继续观察,谨慎操作")
                else:
                    print("[ERROR] 回测策略表现不佳(收益率<0%)")
                    print("   建议: 暂不建议实际交易")

        print(f"{'='*70}\n")

        # 借鉴主流量化框架：绩效指标（Sharpe/回撤/Calmar/成本感知）
        perf_metrics = _qm.summarize(
            self.strategy.equity_curve,
            initial_capital=self.strategy.initial_cash,
            costs=[self.strategy.total_cost] if self.strategy.total_cost > 0 else None,
            turnover_total=self.strategy.total_turnover,
        )
        wf_folds = _qm.walk_forward_split(len(self.strategy.equity_curve), train_ratio=0.7, min_train=60)

        if perf_metrics:
            print(f"\n[PERF] 绩效指标（成本感知，借鉴 quantstats/vectorbt）")
            print(f"{'-'*70}")
            print(f"夏普比率: {perf_metrics.get('sharpe', 0):.2f}   索提诺: {perf_metrics.get('sortino', 0):.2f}   卡玛: {perf_metrics.get('calmar', 0):.2f}")
            print(f"最大回撤: {perf_metrics.get('max_drawdown', 0):.2f}%   年化收益: {perf_metrics.get('annualized_return', 0):.2f}%   年化波动: {perf_metrics.get('annualized_volatility', 0):.2f}%")
            print(f"95%VaR: {perf_metrics.get('var_95', 0):.2f}%   95%CVaR: {perf_metrics.get('cvar_95', 0):.2f}%")
            if 'net_return_after_cost' in perf_metrics:
                print(f"累计交易成本: {perf_metrics.get('total_cost', 0):,.0f} 元（占初始资金 {perf_metrics.get('cost_ratio_pct', 0):.4f}%）")
                print(f"净利(成本后): {perf_metrics.get('net_return_after_cost', 0):.2f}%   毛利: {perf_metrics.get('gross_return', 0):.2f}%")
        if wf_folds:
            print(f"[WF] walk-forward 校验：可分 {len(wf_folds)} 折（训练70%/测试30%滚动）")

        return {
            'model_name': self.strategy.ai_optimizer.name,
            'returns': returns,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'buy_hold_return': buy_hold_return,
            'final_value': final_value,
            'total_cost': round(self.strategy.total_cost, 2),
            'total_turnover': round(self.strategy.total_turnover, 2),
            'commission_rate': self.strategy.commission_rate,
            'slippage_rate': self.strategy.slippage_rate,
            'perf': perf_metrics,
            'walk_forward_folds': len(wf_folds) if wf_folds else 0,
        }

    def run_combined_backtest(self, data_map):
        """多股票组合回测：共享一个资金账户，按共同交易日同时交易多只股票。
        data_map: {code: DataFrame(原始日线: 日期/收盘/成交量...)}
        返回含 per_stock 明细的 dict。"""
        import pandas as _pd
        if not data_map:
            return None
        # 1) 预处理每只股票
        prepared = {}
        for code, df in data_map.items():
            if df is None or df.empty:
                continue
            try:
                df = self._normalize_column_names(df.copy())
            except Exception:
                continue
            if not {'日期', '收盘', '成交量'}.issubset(df.columns) or len(df) < 60:
                continue
            try:
                df = self.strategy.calculate_indicators(df)
            except Exception:
                continue
            df = df.reset_index(drop=True)
            prepared[code] = df
        if not prepared:
            print("[ERROR] 组合回测：无有效股票数据")
            return None

        # 2) AI 训练（跨股票拼接训练，特征一致）
        if self.use_ai:
            print(f"\n[STAT] 组合AI学习历史数据（{len(prepared)} 只股票）...")
            concat_df = _pd.concat([d.copy() for d in prepared.values()], ignore_index=True)
            if not self.strategy.ai_optimizer.train_model(concat_df):
                return None

        # 3) 共同交易日对齐（统一为 YYYY-MM-DD 字符串）
        def _dstr(x):
            s = str(x).strip()
            return s[:10] if s else s
        date_sets = [set(df['日期'].astype(str).map(_dstr)) for df in prepared.values()]
        common_dates = sorted(set.intersection(*date_sets))
        if len(common_dates) < 60:
            print(f"[WARN] 共同交易日不足（{len(common_dates)}天），无法组合回测")
            return None
        pos_map = {code: {_dstr(d): i for i, d in enumerate(df['日期'])} for code, df in prepared.items()}
        last_price = {code: float(df.iloc[-1]['收盘']) for code, df in prepared.items()}
        last_date = {code: _dstr(df.iloc[-1]['日期']) for code, df in prepared.items()}

        # 4) 逐共同交易日执行：每只股票独立信号，共享资金与持仓
        print(f"\n[MONEY] 组合回测执行中（{len(common_dates)} 个共同交易日）...")
        buy_count = sell_count = 0
        capital_skipped = set()
        for d in common_dates:
            for code, df in prepared.items():
                i = pos_map[code].get(d)
                if i is None or i < 60:
                    continue
                cur = df.iloc[i]
                price = float(cur['收盘'])
                if self.strategy.buy_signal(df, i) and code not in self.strategy.positions:
                    volume = int((self.strategy.cash * 0.3) / (price * 100))
                    if volume <= 0 and self.strategy.cash >= price * 100:
                        volume = 1
                    if volume <= 0 and self.strategy.cash < price * 100:
                        capital_skipped.add((code, price))
                        continue
                    if volume > 0:
                        self.strategy.execute_trade(code, 'buy', price, volume, _dstr(cur['日期']))
                        buy_count += 1
                        print(f"  [UP] [买入] {_dstr(cur['日期'])} {code} 价格: {price:.2f} 数量: {volume} 手")
                elif self.strategy.sell_signal(df, i) and code in self.strategy.positions:
                    volume = self.strategy.positions[code]
                    self.strategy.execute_trade(code, 'sell', price, volume, _dstr(cur['日期']))
                    sell_count += 1
                    print(f"  [DOWN] [卖出] {_dstr(cur['日期'])} {code} 价格: {price:.2f} 数量: {volume} 手")

        # 5) 期末对仍持仓的股票按各自最后收盘价平仓
        for code in list(self.strategy.positions):
            if code in last_price:
                volume = self.strategy.positions[code]
                self.strategy.execute_trade(code, 'sell', last_price[code], volume, last_date.get(code, ''))
                sell_count += 1
                print(f"  [LOCK] [平仓] {code} 价格: {last_price[code]:.2f} 数量: {volume} 手")

        # 6) 指标汇总
        final_value = self.strategy.cash
        returns = (final_value - self.strategy.initial_cash) / self.strategy.initial_cash * 100

        # 胜率：按股票配对 buy→sell
        buys = {}
        win_trades = total_trades = 0
        for t in self.strategy.trade_history:
            st = str(t.get('stock') or t.get('code') or '')
            if t.get('action') == 'buy':
                buys.setdefault(st, []).append(t['price'])
            elif t.get('action') == 'sell':
                q = buys.get(st)
                if q:
                    total_trades += 1
                    if t['price'] > q.pop(0):
                        win_trades += 1
        win_rate = win_trades / total_trades if total_trades else 0

        # 买入持有收益：等权平均各股
        bh = []
        for code, df in prepared.items():
            try:
                sp = float(df.iloc[0]['收盘'])
                ep = float(df.iloc[-1]['收盘'])
                if sp:
                    bh.append((ep - sp) / sp * 100)
            except Exception:
                pass
        buy_hold_return = sum(bh) / len(bh) if bh else 0.0

        # AI 学习优化
        if self.use_ai:
            try:
                self.strategy.ai_optimizer.optimize_parameters(
                    {'returns': returns, 'win_rate': win_rate, 'total_trades': total_trades})
                self.strategy.ai_optimizer.save_model()
            except Exception:
                pass

        print(f"\n{'='*70}\n[STAT] 组合回测结果")
        print(f"股票数: {len(prepared)}  交易: 买{buy_count}/卖{sell_count}")
        print(f"胜率: {win_rate*100:.2f}% ({win_trades}/{total_trades})")
        print(f"最终资产: {final_value:,.2f} 元  收益率: {returns:.2f}%  买入持有: {buy_hold_return:.2f}%")
        if capital_skipped:
            skip_detail = '、'.join('%s(1手约%.0f元)' % (c, p * 100) for c, p in sorted(capital_skipped, key=lambda x: x[1], reverse=True))
            print(f"[WARN] 以下股票因资金不足（1手 > 初始资金 {self.strategy.initial_cash:,.0f} 元）无法买入: {skip_detail}")
        per = []
        for code, df in prepared.items():
            try:
                sp = float(df.iloc[0]['收盘']); ep = float(df.iloc[-1]['收盘'])
                per.append({'code': code, 'name': str(code), 'buy_hold': round((ep - sp) / sp * 100, 2) if sp else 0})
            except Exception:
                pass
        print(f"{'='*70}\n")
        return {
            'model_name': self.strategy.ai_optimizer.name,
            'returns': returns,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'buy_hold_return': buy_hold_return,
            'final_value': final_value,
            'stock_count': len(prepared),
            'initial_cash': self.strategy.initial_cash,
            'capital_skipped': sorted(capital_skipped, key=lambda x: x[1], reverse=True),
            'per_stock': per,
            # 借鉴主流量化框架：绩效指标（Sharpe/回撤/Calmar/成本感知）
            'total_cost': round(self.strategy.total_cost, 2),
            'total_turnover': round(self.strategy.total_turnover, 2),
            'commission_rate': self.strategy.commission_rate,
            'slippage_rate': self.strategy.slippage_rate,
            'perf': _qm.summarize(
                self.strategy.equity_curve,
                initial_capital=self.strategy.initial_cash,
                costs=[self.strategy.total_cost] if self.strategy.total_cost > 0 else None,
                turnover_total=self.strategy.total_turnover,
            ),
            'walk_forward_folds': len(_qm.walk_forward_split(
                len(self.strategy.equity_curve), train_ratio=0.7, min_train=60)),
        }


def show_model_selection():
    """显示模型选择菜单"""
    print("\n" + "="*70)
    print("[BOOK] 可用的AI模型列表")
    print("="*70)
    
    for key, info in AI_MODELS.items():
        print(f"\n[{key}] {info['name']}")
        print(f"    描述: {info['description']}")
        print(f"    速度: {info['speed']}  |  精度: {info['accuracy']}")
    
    print("\n" + "="*70)


def compare_models(stock_code, start_date, end_date, model_types):
    """对比多个模型"""
    print("\n" + "="*70)
    print("[TGT] 多模型对比回测")
    print("="*70)
    
    results = []
    
    for model_type in model_types:
        print(f"\n{'*'*70}")
        print(f"正在测试模型: {AI_MODELS[model_type]['name']}")
        print(f"{'*'*70}")
        
        backtester = MultiModelBacktester(model_type=model_type, use_ai=True)
        result = backtester.run_backtest(stock_code, start_date, end_date)
        
        if result:
            results.append(result)
        
        time.sleep(1)  # 避免请求过快
    
    # 显示对比结果
    if results:
        print("\n" + "="*70)
        print("[STAT] 模型对比总结")
        print("="*70)
        print(f"{'模型名称':<30} {'收益率':<10} {'胜率':<10} {'交易次数':<10}")
        print("-"*70)
        
        for result in sorted(results, key=lambda x: x['returns'], reverse=True):
            print(f"{result['model_name']:<30} "
                  f"{result['returns']:>8.2f}%  "
                  f"{result['win_rate']*100:>7.2f}%  "
                  f"{result['total_trades']:>8}")
        
        print("="*70)
        
        # 找出最佳模型
        best = max(results, key=lambda x: x['returns'])
        print(f"\n🏆 最佳模型: {best['model_name']}")
        print(f"   收益率: {best['returns']:.2f}%")
        print(f"   胜率: {best['win_rate']*100:.2f}%")


class RealTimeMonitor:
    """实时监控器 - 支持批量股票监控"""

    def __init__(self, stock_codes, model_type='1', refresh_interval=60, portfolio_manager=None):
        """
        初始化监控器
        stock_codes: 股票代码列表
        model_type: AI模型类型
        refresh_interval: 刷新间隔(秒)
        portfolio_manager: 持仓管理器
        """
        self.stock_codes = stock_codes
        self.model_type = model_type
        self.refresh_interval = refresh_interval
        self.crawler = FinancialDataCrawler()
        self.strategies = {}
        self.running = True
        self.portfolio_manager = portfolio_manager  # 持仓管理器

        # 为每个股票创建策略实例
        for stock in stock_codes:
            strategy = AITradingStrategy(model_type=model_type, use_ai=True)
            self.strategies[stock] = strategy

            # 尝试加载已训练的模型
            model_file = f'ai_model_{model_type}_{stock}.pkl'
            strategy.ai_optimizer.load_model(model_file)

        print(f"\n✓ 监控器初始化完成")
        print(f"  监控股票: {', '.join(stock_codes)}")
        print(f"  AI模型: {AI_MODELS[model_type]['name']}")
        print(f"  刷新间隔: {refresh_interval}秒")
        if self.portfolio_manager:
            print(f"  持仓管理: 已启用")
    
    def train_models(self):
        """训练所有股票的模型"""
        print("\n" + "="*70)
        print("[BOT] 开始训练AI模型...")
        print("="*70)
        
        current_year = datetime.now().year
        start_date = f"{current_year}0101"
        end_date = datetime.now().strftime('%Y%m%d')
        
        for stock_code in self.stock_codes:
            print(f"\n[STAT] [{stock_code}] 获取历史数据...")
            df = self.crawler.get_stock_data(stock_code, start_date, end_date)
            
            if df is None or df.empty or len(df) < 60:
                print(f"[WARN]  [{stock_code}] 数据不足，跳过")
                continue
            
            # 计算技术指标
            df = self.strategies[stock_code].calculate_indicators(df)
            
            # 训练模型
            success = self.strategies[stock_code].ai_optimizer.train_model(df)
            
            if success:
                # 保存模型
                model_file = f'ai_model_{self.model_type}_{stock_code}.pkl'
                self.strategies[stock_code].ai_optimizer.save_model(model_file)
            
            time.sleep(1)  # 避免请求过快
        
        print("\n✓ 所有模型训练完成！")
    
    def _check_models_need_training(self):
        """检查是否需要训练模型"""
        import os
        import glob
        
        # 检查是否有已训练的模型文件
        model_files = glob.glob(f"ai_model_{self.model_type}_*.pkl")
        
        # 如果没有模型文件，需要训练
        if not model_files:
            print("[WARN]  未找到已训练的AI模型文件")
            return True
        
        # 检查模型文件是否完整
        for stock_code in self.stock_codes:
            model_file = f"ai_model_{self.model_type}_{stock_code}.pkl"
            if not os.path.exists(model_file):
                print(f"[WARN]  未找到股票 {stock_code} 的AI模型文件")
                return True
            
            # 检查模型文件大小（太小的文件可能有问题）
            file_size = os.path.getsize(model_file)
            if file_size < 1000:  # 小于1KB的模型文件可能有问题
                print(f"[WARN]  股票 {stock_code} 的模型文件过小，需要重新训练")
                return True
        
        print(f"✓ 检测到 {len(model_files)} 个已训练的AI模型文件")
        return False
    
    def check_key_press(self):
        """检查是否按下q键（仅 Windows 命令行环境）"""
        if not HAS_MSVCRT:
            return False
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key.lower() == b'q':
                return True
        return False
    
    def get_realtime_signal(self, stock_code):
        """获取实时交易信号"""
        try:
            # 获取最近60天数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            
            df = self.crawler.get_stock_data(stock_code, start_date, end_date)
            
            if df is None or df.empty or len(df) < 60:
                return None
            
            # 计算技术指标
            df = self.strategies[stock_code].calculate_indicators(df)
            
            # 获取最新数据
            latest_idx = len(df) - 1
            latest = df.iloc[latest_idx]
            
            # 判断信号
            buy_signal = self.strategies[stock_code].buy_signal(df, latest_idx)
            sell_signal = self.strategies[stock_code].sell_signal(df, latest_idx)
            
            # AI预测信号
            ai_signal = 0
            if self.strategies[stock_code].ai_optimizer.is_trained:
                ai_signal = self.strategies[stock_code].ai_optimizer.predict_signal(df, latest_idx)
            
            # 计算涨跌幅
            if latest_idx > 0:
                prev_close = df.iloc[latest_idx - 1]['收盘']
                change_pct = (latest['收盘'] - prev_close) / prev_close * 100
            else:
                change_pct = 0
            
            # 如果有持仓管理器且该股票有持仓,更新当前价格
            if self.portfolio_manager and self.portfolio_manager.has_position(stock_code):
                current_price = latest['收盘']
                self.portfolio_manager.update_all_prices({stock_code: current_price})

            return {
                'stock_code': stock_code,
                'date': latest['日期'],
                'price': latest['收盘'],
                'change_pct': change_pct,
                'volume': latest['成交量'],
                'buy_signal': buy_signal,
                'sell_signal': sell_signal,
                'ai_signal': ai_signal,
                'rsi': latest.get('RSI', None),
                'macd': latest.get('MACD', None),
                'ma5': latest.get('MA5', None),
                'ma20': latest.get('MA20', None)
            }
            
        except Exception as e:
            print(f"[ERROR] [{stock_code}] 获取数据失败: {e}")
            return None
    
    def display_signals(self, signals):
        """显示交易信号"""
        print("\n" + "="*120)
        print(f"[STAT] 实时监控面板 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*120)

        # 显示持仓信息
        if self.portfolio_manager:
            portfolio_value = self.portfolio_manager.get_total_value()
            portfolio_profit = self.portfolio_manager.get_total_profit_loss()
            portfolio_profit_pct = self.portfolio_manager.get_total_profit_loss_pct()
            print(f"\n[WORK] 当前持仓: 总资产 {portfolio_value:,.2f} 元 | 盈亏 {portfolio_profit:+,.2f} 元 ({portfolio_profit_pct:+.2f}%)")
            print("="*120)

        # 表头
        print(f"{'股票代码':<10} {'最新价':<10} {'涨跌幅':<10} {'RSI':<8} {'MACD':<10} {'AI信号':<10} {'操作建议':<20} {'AI交易建议':<25}")
        print("-"*120)

        for signal in signals:
            if signal is None:
                continue

            # 涨跌幅颜色
            change_str = f"{signal['change_pct']:>+7.2f}%"

            # AI信号
            if signal['ai_signal'] == 1:
                ai_str = "看涨 ↑"
            elif signal['ai_signal'] == -1:
                ai_str = "看跌 ↓"
            else:
                ai_str = "中性 -"

            # 操作建议
            if signal['buy_signal']:
                action = "🟢 买入信号"
            elif signal['sell_signal']:
                action = "🔴 卖出信号"
            else:
                action = "⚪ 观望"

            # AI交易建议(基于持仓)
            ai_recommendation = ""
            if self.portfolio_manager:
                trade_signal, reason = self.portfolio_manager.get_ai_trading_signal(
                    signal['stock_code'],
                    signal['ai_signal'],
                    signal['price']
                )
                if trade_signal == 'BUY':
                    ai_recommendation = f"🟢 {reason}"
                elif trade_signal == 'SELL':
                    ai_recommendation = f"🔴 {reason}"
                else:
                    ai_recommendation = f"⚪ {reason}"

            # RSI和MACD
            rsi_str = f"{signal['rsi']:.1f}" if signal['rsi'] is not None and pd.notna(signal['rsi']) else "N/A"
            macd_str = f"{signal['macd']:.3f}" if signal['macd'] is not None and pd.notna(signal['macd']) else "N/A"

            print(f"{signal['stock_code']:<10} "
                  f"{signal['price']:<10.2f} "
                  f"{change_str:<10} "
                  f"{rsi_str:<8} "
                  f"{macd_str:<10} "
                  f"{ai_str:<10} "
                  f"{action:<20} "
                  f"{ai_recommendation:<25}")

        print("="*120)
        print(f"[IDEA] 提示: 按 'q' 键退出监控 | 下次刷新: {self.refresh_interval}秒后")
        print("="*120)

    def start_monitoring(self, auto_train=False):
        """开始实时监控"""
        print("\n[RUN] 启动实时监控...")
        print("="*70)
        
        # 自动判断是否需要训练模型
        need_training = auto_train or self._check_models_need_training()
        
        if need_training:
            print("\n[BOT] 检测到需要训练AI模型，开始自动训练...")
            self.train_models()
        else:
            print("\n✓ 使用已训练的AI模型进行监控")
        
        print("\n✓ 监控开始！")
        print("  按 'q' 键可随时退出监控\n")
        
        cycle_count = 0
        
        while self.running:
            cycle_count += 1
            
            # 获取所有股票的信号（快速检查停止标志）
            signals = []
            for i, stock_code in enumerate(self.stock_codes):
                if not self.running:  # 立即检查停止标志
                    break
                signal = self.get_realtime_signal(stock_code)
                signals.append(signal)
                
                # 每隔几只股票检查一次停止标志，减少延迟
                if i % 2 == 0:
                    time.sleep(0.1)  # 更短的延迟
                else:
                    time.sleep(0.05)
            
            if not self.running:
                break
            
            # 显示信号
            self.display_signals(signals)
            
            # 快速等待刷新间隔（每0.1秒检查一次停止标志）
            print(f"\n⏳ 等待{self.refresh_interval}秒...(按 'q' 或点击停止按钮退出)", end='', flush=True)
            
            wait_seconds = 0
            while wait_seconds < self.refresh_interval and self.running:
                # 每0.1秒检查一次，提高响应速度
                time.sleep(0.1)
                wait_seconds += 0.1
                
                # 检查是否按下q键
                if self.check_key_press():
                    print("\n\n🛑 检测到退出信号...")
                    self.running = False
                    break
                
                # 每5秒更新一次显示，减少频繁输出
                if wait_seconds % 5 < 0.1:
                    remaining = max(0, self.refresh_interval - wait_seconds)
                    print(f"\r⏳ 等待{int(remaining)}秒...(按 'q' 或点击停止按钮退出)    ", end='', flush=True)
            
            print()  # 换行
        
        print("\n" + "="*70)
        print(f"✓ 监控结束 - 共运行 {cycle_count} 个周期")
        print("="*70)


def parse_stock_codes(input_str):
    """解析股票代码输入"""
    # 支持逗号、空格、分号分隔
    codes = []
    for separator in [',', ' ', ';', '，', '、']:
        input_str = input_str.replace(separator, ',')
    
    for code in input_str.split(','):
        code = code.strip()
        if code:
            codes.append(code)
    
    return codes


def main():
    """主程序"""
    print("="*70)
    print("[BOT] 多模型AI量化交易系统")
    print("支持8种机器学习模型选择和对比")
    print("="*70)
    
    while True:
        print("\n请选择功能:")
        print("1. 查看所有AI模型")
        print("2. 单模型回测")
        print("3. 多模型对比回测")
        print("4. 批量股票实时监控 [STAR]NEW")
        print("5. 退出")
        
        choice = input("\n请输入选项 (1-5): ").strip()
        
        if choice == '1':
            show_model_selection()
        
        elif choice == '2':
            # 单模型回测
            show_model_selection()
            model_type = input("\n请选择模型 (1-8): ").strip()
            
            if model_type not in AI_MODELS:
                print("[ERROR] 无效的模型选择")
                continue
            
            stock_code = input("请输入股票代码 (如 000001): ").strip()
            
            current_year = datetime.now().year
            start_date = f"{current_year}0101"
            end_date = datetime.now().strftime('%Y%m%d')
            
            backtester = MultiModelBacktester(model_type=model_type, use_ai=True)
            backtester.run_backtest(stock_code, start_date, end_date)
        
        elif choice == '3':
            # 多模型对比
            stock_code = input("请输入股票代码 (如 000001): ").strip()
            
            print("\n选择要对比的模型（用逗号分隔，如: 1,2,3）")
            print("或输入 'all' 对比所有模型")
            show_model_selection()
            
            model_input = input("\n请输入: ").strip()
            
            if model_input.lower() == 'all':
                model_types = list(AI_MODELS.keys())
            else:
                model_types = [m.strip() for m in model_input.split(',') if m.strip() in AI_MODELS]
            
            if not model_types:
                print("[ERROR] 无效的模型选择")
                continue
            
            current_year = datetime.now().year
            start_date = f"{current_year}0101"
            end_date = datetime.now().strftime('%Y%m%d')
            
            compare_models(stock_code, start_date, end_date, model_types)
        
        elif choice == '4':
            # 批量股票实时监控
            print("\n" + "="*70)
            print("📡 批量股票实时监控")
            print("="*70)
            
            print("\n请输入股票代码（支持批量输入）:")
            print("  格式示例1: 000001,000002,600000")
            print("  格式示例2: 000001 000002 600000")
            print("  格式示例3: 000001，000002，600000")
            
            stock_input = input("\n请输入: ").strip()
            stock_codes = parse_stock_codes(stock_input)
            
            if not stock_codes:
                print("[ERROR] 未输入有效的股票代码")
                continue
            
            print(f"\n✓ 已识别 {len(stock_codes)} 只股票: {', '.join(stock_codes)}")
            
            # 选择模型
            show_model_selection()
            model_type = input("\n请选择监控使用的AI模型 (1-8, 默认1): ").strip()
            if not model_type or model_type not in AI_MODELS:
                model_type = '1'
                print(f"使用默认模型: {AI_MODELS['1']['name']}")
            
            # 设置刷新间隔
            interval_input = input("\n请输入刷新间隔(秒, 默认60): ").strip()
            try:
                refresh_interval = int(interval_input) if interval_input else 60
                if refresh_interval < 10:
                    refresh_interval = 10
                    print("[WARN]  刷新间隔最小为10秒")
            except:
                refresh_interval = 60
                print("使用默认刷新间隔: 60秒")
            
            # 创建监控器
            monitor = RealTimeMonitor(stock_codes, model_type, refresh_interval)
            
            # 开始监控
            monitor.start_monitoring()
        
        elif choice == '5':
            print("\n👋 感谢使用！")
            break
        
        else:
            print("[ERROR] 无效选项，请重新选择")


if __name__ == "__main__":
    main()
