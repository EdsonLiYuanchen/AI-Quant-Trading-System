---
name: AI量化交易系统
version: v2.0.0
description: 集数据爬取、AI分析、策略回测和实时监控于一体的量化交易系统
license: MIT
---

# 🤖 AI量化交易系统 v2.0

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Stable-success.svg)]()

**一个集数据爬取、AI分析、策略回测和实时监控于一体的量化交易系统**

</div>

---

## ✨ 功能特性

### 🎯 核心功能

| 功能模块 | 说明 | 状态 |
|---------|------|------|
| 📥 **数据爬取** | 支持批量下载股票历史数据 | ✅ |
| 🤖 **AI回测** | 8种机器学习模型可选 | ✅ |
| 📡 **实时监控** | 多股票实时监控与AI预测 | ✅ |
| 📊 **数据分析** | 自动生成HTML可视化报告 | ✅ |
| 🎨 **图形界面** | 现代化GUI，操作简单 | ✅ |
| 🌐 **Web界面** | 浏览器访问的Web版本 | ✅ |
| 🧵 **多线程** | 异步处理，界面不卡顿 | ✅ |

### 🧠 AI模型支持

- ✅ 随机森林 (Random Forest) - 速度快，精度高
- ✅ 梯度提升树 (Gradient Boosting) - 精度很高
- ✅ 神经网络 (Neural Network) - 学习能力强
- ✅ 逻辑回归 (Logistic Regression) - 速度最快
- ✅ 支持向量机 (SVM) - 精度高
- ✅ AdaBoost - 自适应提升
- ✅ 决策树 (Decision Tree) - 简单直观
- ✅ 朴素贝叶斯 (Naive Bayes) - 速度快

### 📈 技术指标

- **均线系统**: MA5, MA10, MA20, MA60
- **趋势指标**: MACD, DIF, DEA
- **摆动指标**: RSI (相对强弱指标)
- **通道指标**: 布林带 (Bollinger Bands)
- **成交量**: VOL, VOL_MA5, VOL_MA10

---

## 🚀 快速开始

### 📋 前置要求

- Python 3.8 或更高版本
- Windows 10/11
- 至少 4GB 内存

### 📦 安装步骤

#### 方法一：直接使用可执行文件（推荐）

1. 从 [Releases](https://github.com/EdsonLiYuanchen/AI-Quant-Trading-System/releases) 下载最新版本的安装包
2. 解压后双击 `AI_Trading_System.exe` 启动

#### 方法二：从源码运行

```bash
# 1. 克隆项目
git clone https://github.com/EdsonLiYuanchen/AI-Quant-Trading-System.git
cd AI-Quant-Trading-System/程序本体

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动GUI版本
python AI量化交易系统GUI.py

# 或者启动Web版本
python AI量化交易系统Web.py
```

---

## 📁 项目结构

```
AI-Quant-Trading-System/
├── 程序本体/                    # 源代码目录
│   ├── AI量化交易系统GUI.py     # 主程序（图形界面）
│   ├── AI量化交易系统Web.py     # Web界面版本
│   ├── 多模型AI量化交易.py      # AI模型和策略
│   ├── 爬取金融数据.py          # 数据爬取模块
│   ├── 分析数据.py              # 数据分析模块
│   ├── requirements.txt         # Python依赖
│   └── README.md               # 详细说明文档
├── dist/                       # 构建输出
│   ├── AI_Trading_System.exe   # 可执行文件 (31MB)
│   └── AI量化交易系统_便携版.zip # 便携版 (114MB)
├── .gitignore                  # Git忽略规则
└── README.md                   # 本文件
```

---

## 📥 下载

### Windows 可执行文件

| 文件 | 大小 | 说明 |
|------|------|------|
| [AI_Trading_System.exe](dist/AI_Trading_System.exe) | 31 MB | 单文件可执行程序，双击即可运行 |
| [AI量化交易系统_便携版.zip](dist/AI量化交易系统_便携版.zip) | 114 MB | 便携版，无需安装，解压即用 |

> 💡 **提示**: 便携版包含所有依赖，可直接拷贝到其他Windows机器运行。

---

## 🧪 冒烟测试

已完成以下核心模块的导入测试：

```
✅ akshare (1.18.8)
✅ customtkinter (OK)
✅ scikit-learn (1.7.2)
✅ pandas (2.3.3)
✅ webview (OK)
✅ bottle (0.13.4)
✅ 爬取金融数据 (FinancialDataCrawler)
✅ 分析数据 (FinancialDataAnalyzer)
✅ 多模型AI量化交易 (MultiModelBacktester)
✅ ai_strategy (OK)
✅ database_manager (DatabaseManager)
✅ quant_metrics (OK)
✅ dynamic_stock_picker (OK)
✅ fund_search_tool (OK)
✅ stock_trading_api (OK)
✅ auto_trading_engine (OK)
✅ capital_rebalancer (OK)
✅ AI量化交易系统Web (OK)
```

**测试结果**: 12/12 核心模块导入成功 ✅

---

## 📖 使用说明

### 1️⃣ 数据爬取

```
功能：批量下载股票历史数据

步骤：
1. 输入股票代码（支持批量）
   单个: 000001
   批量: 000001,000002,600000
2. 设置时间范围
3. 点击"开始爬取"

数据保存在: 金融数据/ 文件夹
```

### 2️⃣ AI回测

```
功能：测试AI交易策略表现

步骤：
1. 输入股票代码
2. 选择AI模型
3. 点击"开始回测"

输出指标：
- 收益率
- 胜率
- 交易次数
- 超额收益
```

### 3️⃣ 实时监控

```
功能：实时监控多只股票并给出交易建议

步骤：
1. 输入股票代码（支持批量）
2. 选择AI模型
3. 设置刷新间隔
4. 点击"开始监控"

显示信息：
- 最新价格
- 涨跌幅
- RSI/MACD指标
- AI预测信号
- 操作建议（买入/卖出/观望）
```

### 4️⃣ 数据分析

```
功能：生成数据分析HTML报告

步骤：
1. 确认数据目录
2. 可选：启用AI分析
3. 点击"开始分析"

报告包含：
- 数据基本信息
- 统计分析
- 数据洞察
- 可视化图表
```

---

## 🔧 高级配置

### 自定义数据路径

编辑 `爬取金融数据.py`:
```python
DATA_DIR = r"你的自定义路径"
```

### 调整AI模型参数

编辑 `多模型AI量化交易.py`:
```python
AI_MODELS = {
    '1': {
        'params': {
            'n_estimators': 100,  # 调整这里
            'max_depth': 10,
            'random_state': 42
        }
    }
}
```

---

## ❓ 常见问题

**Q: 程序启动失败怎么办？**

检查以下几点：
1. Python版本是否 >= 3.8
2. 依赖是否已安装（运行`安装依赖.bat`）
3. 查看错误信息，可能缺少某个库

**Q: 数据爬取失败？**

可能原因：
1. 网络连接问题
2. 股票代码错误
3. 数据源服务器繁忙（稍后重试）
4. 尝试更新AKShare: `pip install --upgrade akshare`

**Q: AI预测准确吗？**

注意事项：
1. AI预测是概率性的，不是100%准确
2. 首次使用需要训练模型
3. 历史数据不足会影响准确性
4. 建议结合多个指标综合判断
5. **投资有风险，仅供学习参考！**

---

## 🛣️ 开发路线图

### v2.0 ✅ (当前版本)
- [x] 图形化界面
- [x] Web界面版本
- [x] 批量数据爬取
- [x] 8种AI模型
- [x] 实时监控功能
- [x] 数据分析报告
- [x] 基金交易支持

### v2.1 🚧 (计划中)
- [ ] 数据可视化图表
- [ ] 更多技术指标
- [ ] 策略回测优化
- [ ] 模型参数自动调优

---

## 🤝 贡献指南

欢迎贡献代码！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📜 免责声明

⚠️ **重要提示**

1. 本项目**仅供学习和研究使用**
2. **不构成任何投资建议**
3. **投资有风险，入市需谨慎**
4. 使用本软件进行交易的任何盈亏，开发者不承担任何责任
5. 请在充分了解风险的前提下使用

---


---

## 📦 下载 Release v2.0.0

| 文件 | 大小 | 说明 | 下载 |
|------|------|------|------|
| AI_Trading_System_v2.0.0.exe | 31.3 MB | 独立可执行文件，无需安装 | [点击下载](https://github.com/EdsonLiYuanchen/AI-Quant-Trading-System/releases/download/v2.0.0/AI_Trading_System_v2.0.0.exe) |
| AI_Quant_System_Portable_v2.0.0.zip | 114.4 MB | 便携版，含完整运行环境 | [点击下载](https://github.com/EdsonLiYuanchen/AI-Quant-Trading-System/releases/download/v2.0.0/AI_Quant_System_Portable_v2.0.0.zip) |

---
## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 📞 联系方式

- 💬 Issues: [GitHub Issues](https://github.com/EdsonLiYuanchen/AI-Quant-Trading-System/issues)
- 📖 文档: [程序本体/README.md](程序本体/README.md)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个星标！**

Made with ❤️ by AI量化团队

</div>
