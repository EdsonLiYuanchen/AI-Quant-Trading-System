# 🤖 AI量化交易系统 v2.0.0 发布说明

**发布日期**: 2026-10-24

## ✨ 版本概述

AI量化交易系统 v2.0.0 是一个集数据爬取、AI分析、策略回测和实时监控于一体的量化交易工具。本版本支持8种机器学习模型，提供GUI和Web两种界面模式。

---

## 🧪 冒烟测试结果

```
✅ 核心模块导入测试: 12/12 通过
✅ Python版本: 3.13.7
✅ akshare: 1.18.8
✅ scikit-learn: 1.7.2
✅ pandas: 2.3.3
✅ webview: OK
✅ bottle: 0.13.4
```

### 测试通过的模块
- [x] 爬取金融数据 (FinancialDataCrawler)
- [x] 分析数据 (FinancialDataAnalyzer)
- [x] 多模型AI量化交易 (MultiModelBacktester)
- [x] ai_strategy
- [x] database_manager (DatabaseManager)
- [x] quant_metrics
- [x] dynamic_stock_picker
- [x] fund_search_tool
- [x] stock_trading_api
- [x] auto_trading_engine
- [x] capital_rebalancer
- [x] AI量化交易系统Web

---

## 📦 下载文件

| 文件名 | 大小 | 说明 |
|--------|------|------|
| `AI_Trading_System.exe` | 31.28 MB | 单文件可执行程序，双击运行 |
| `AI量化交易系统_便携版.zip` | 114.35 MB | 便携版，包含所有依赖 |

### 文件大小详情

```
AI_Trading_System.exe          32,796,604 bytes (31.28 MB)
AI量化交易系统_便携版.zip      119,909,569 bytes (114.35 MB)
```

---

## 🚀 快速开始

### 方式一：使用可执行文件
1. 下载 `AI_Trading_System.exe`
2. 双击运行即可启动GUI界面

### 方式二：使用便携版
1. 下载 `AI量化交易系统_便携版.zip`
2. 解压到任意目录
3. 双击 `启动.bat` 运行

### 方式三：从源码运行
```bash
git clone https://github.com/Edson-Li/AI-Quant-Trading-System.git
cd AI-Quant-Trading-System/程序本体
pip install -r requirements.txt
python AI量化交易系统GUI.py
```

---

## 📋 功能清单

### ✅ 已完成功能

| 功能 | 说明 |
|------|------|
| 数据爬取 | 支持批量下载A股历史数据 |
| AI回测 | 8种机器学习模型回测 |
| 实时监控 | 多股票实时行情监控 |
| 数据分析 | 自动生成HTML分析报告 |
| GUI界面 | CustomTkinter现代化界面 |
| Web界面 | 浏览器访问的Web版本 |
| 基金交易 | 支持基金搜索和交易 |
| 数据库 | SQLite/MySQL双支持 |

### 🧠 AI模型列表

1. 随机森林 (Random Forest)
2. 梯度提升树 (Gradient Boosting)
3. 神经网络 (Neural Network)
4. 逻辑回归 (Logistic Regression)
5. 支持向量机 (SVM)
6. AdaBoost
7. 决策树 (Decision Tree)
8. 朴素贝叶斯 (Naive Bayes)

---

## 📊 技术指标支持

- 均线系统: MA5, MA10, MA20, MA60
- MACD: DIF, DEA, MACD柱
- RSI: 相对强弱指标
- 布林带: Bollinger Bands
- 成交量: VOL, VOL_MA5, VOL_MA10

---

## 🔧 系统要求

- **操作系统**: Windows 10/11
- **内存**: 至少 4GB
- **磁盘空间**: 至少 1GB 可用空间
- **Python**: 3.8+ (仅源码运行需要)

---

## ⚠️ 免责声明

**重要提示**：

1. 本软件**仅供学习和研究使用**
2. **不构成任何投资建议**
3. **投资有风险，入市需谨慎**
4. 使用本软件进行交易的任何盈亏，开发者不承担任何责任
5. 请在充分了解风险的前提下使用

---

## 📝 已知问题

- 首次运行需要等待模型初始化
- 数据爬取依赖网络连接
- 部分功能需要互联网访问

---

## 🔗 相关链接

- [GitHub 仓库](https://github.com/Edson-Li/AI-Quant-Trading-System)
- [ISSUES](https://github.com/Edson-Li/AI-Quant-Trading-System/issues)
- [完整文档](../程序本体/README.md)

---

<div align="center">

**Made with ❤️ by AI量化团队**

</div>
