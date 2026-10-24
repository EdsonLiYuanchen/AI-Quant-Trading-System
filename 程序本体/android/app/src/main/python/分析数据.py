
"""
金融数据分析程序
功能：读取金融数据文件夹中的数据，进行全面分析，并生成HTML报告
集成AI模型进行智能分析
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import json
import requests
warnings.filterwarnings('ignore')

class AIAnalyzer:
    """AI分析助手类 - 支持多种开源AI模型"""
    
    def __init__(self, model_type='ollama', api_url=None, model_name='llama2'):
        """
        初始化AI分析器
        :param model_type: 模型类型 ('ollama', 'openai_compatible', 'local')
        :param api_url: API地址（可选）
        :param model_name: 模型名称
        """
        self.model_type = model_type
        self.model_name = model_name
        self.enabled = False
        
        # 不同模型的默认配置
        if model_type == 'ollama':
            self.api_url = api_url or 'http://localhost:11434/api/generate'
        elif model_type == 'openai_compatible':
            self.api_url = api_url or 'http://localhost:8080/v1/chat/completions'
        else:
            self.api_url = api_url
        
        # 测试连接
        self._test_connection()
    
    def _test_connection(self):
        """测试AI模型连接"""
        try:
            if self.model_type == 'ollama':
                response = requests.post(
                    self.api_url,
                    json={
                        "model": self.model_name,
                        "prompt": "test",
                        "stream": False
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    self.enabled = True
                    print(f"✓ AI模型已连接: {self.model_name} (Ollama)")
            elif self.model_type == 'openai_compatible':
                response = requests.post(
                    self.api_url,
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": "test"}]
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    self.enabled = True
                    print(f"✓ AI模型已连接: {self.model_name}")
        except Exception as e:
            print(f"⚠ AI模型未连接 ({str(e)})，将使用传统分析方法")
            self.enabled = False
    
    def analyze_data_insights(self, data_summary, file_name):
        """
        使用AI模型分析数据并生成洞察
        :param data_summary: 数据摘要信息
        :param file_name: 文件名
        :return: AI生成的洞察列表
        """
        if not self.enabled:
            return []
        
        try:
            # 构建提示词
            prompt = f"""你是一位专业的金融数据分析师。请分析以下数据并提供3-5条专业洞察：

文件名: {file_name}
数据规模: {data_summary.get('总行数', 0)}行 × {data_summary.get('总列数', 0)}列
数值字段: {', '.join(data_summary.get('数值字段', [])[:5])}
缺失值总数: {data_summary.get('缺失值总数', 0)}

请提供简洁专业的分析洞察，每条洞察一句话，专注于：
1. 数据质量评估
2. 潜在的风险点
3. 数据特征分析
4. 实用建议

要求：每条洞察不超过50字，直接返回洞察内容，不需要编号。"""

            # 调用AI模型
            if self.model_type == 'ollama':
                response = requests.post(
                    self.api_url,
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 500
                        }
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_text = result.get('response', '')
                    insights = [line.strip() for line in ai_text.split('\n') if line.strip() and len(line.strip()) > 10]
                    return insights[:5]
            
            elif self.model_type == 'openai_compatible':
                response = requests.post(
                    self.api_url,
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": "你是一位专业的金融数据分析师。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_text = result['choices'][0]['message']['content']
                    insights = [line.strip() for line in ai_text.split('\n') if line.strip() and len(line.strip()) > 10]
                    return insights[:5]
            
        except Exception as e:
            print(f"AI分析出错: {str(e)}")
        
        return []


class FinancialDataAnalyzer:
    def __init__(self, data_path, output_path, enable_ai=False, ai_config=None):
        """
        初始化分析器
        :param data_path: 金融数据文件夹路径
        :param output_path: 分析结果输出路径
        :param enable_ai: 是否启用AI分析
        :param ai_config: AI配置字典 {'model_type': 'ollama', 'model_name': 'llama2', 'api_url': '...'}
        """
        self.data_path = data_path
        self.output_path = output_path
        self.data_files = []
        self.analysis_results = {}
        
        # 初始化AI分析器
        self.ai_analyzer = None
        if enable_ai:
            ai_config = ai_config or {}
            self.ai_analyzer = AIAnalyzer(
                model_type=ai_config.get('model_type', 'ollama'),
                api_url=ai_config.get('api_url'),
                model_name=ai_config.get('model_name', 'llama2')
            )
        
        # 确保输出目录存在
        if not os.path.exists(output_path):
            os.makedirs(output_path)
    
    def scan_data_files(self):
        """扫描数据文件夹中的所有数据文件"""
        print("正在扫描数据文件...")
        supported_extensions = ['.csv', '.xlsx', '.xls', '.txt']
        
        for file in os.listdir(self.data_path):
            file_path = os.path.join(self.data_path, file)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(file)
                if ext.lower() in supported_extensions:
                    self.data_files.append(file_path)
        
        print(f"找到 {len(self.data_files)} 个数据文件")
        return self.data_files
    
    def load_data(self, file_path):
        """加载数据文件"""
        try:
            _, ext = os.path.splitext(file_path)
            if ext.lower() == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8')
            elif ext.lower() == '.txt':
                df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
            elif ext.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                return None
            return df
        except Exception as e:
            print(f"加载文件 {file_path} 失败: {str(e)}")
            return None
    
    def analyze_dataframe(self, df, file_name):
        """分析单个数据框"""
        analysis = {
            'file_name': file_name,
            'basic_info': {},
            'statistical_summary': {},
            'insights': []
        }
        
        # 基础信息
        analysis['basic_info']['总行数'] = len(df)
        analysis['basic_info']['总列数'] = len(df.columns)
        analysis['basic_info']['列名'] = list(df.columns)
        analysis['basic_info']['数据类型'] = df.dtypes.to_dict()
        analysis['basic_info']['缺失值数量'] = df.isnull().sum().to_dict()
        
        # 数值型列的统计分析
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            analysis['statistical_summary']['数值列'] = {}
            for col in numeric_cols:
                col_stats = {
                    '均值': df[col].mean(),
                    '中位数': df[col].median(),
                    '标准差': df[col].std(),
                    '最小值': df[col].min(),
                    '最大值': df[col].max(),
                    '25%分位数': df[col].quantile(0.25),
                    '75%分位数': df[col].quantile(0.75)
                }
                analysis['statistical_summary']['数值列'][col] = col_stats
        
        # 生成洞察
        self.generate_insights(df, analysis)
        
        return analysis
    
    def generate_insights(self, df, analysis):
        """生成数据洞察（结合传统方法和AI分析）"""
        insights = []
        
        # 传统方法生成的基础洞察
        row_count = len(df)
        col_count = len(df.columns)
        insights.append(f"这份数据包含了{row_count}条记录和{col_count}个字段，数据规模{'较大' if row_count > 1000 else '适中' if row_count > 100 else '较小'}。")
        
        # 缺失值洞察
        missing_counts = df.isnull().sum()
        total_missing = missing_counts.sum()
        if total_missing > 0:
            missing_ratio = (total_missing / (len(df) * len(df.columns))) * 100
            insights.append(f"数据存在{total_missing}个缺失值，占总数据量的{missing_ratio:.2f}%。{'需要重点关注数据质量问题' if missing_ratio > 5 else '数据质量整体良好'}。")
        else:
            insights.append("数据完整性极佳，没有发现任何缺失值。")
        
        # 数值列分析洞察
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            insights.append(f"数据包含{len(numeric_cols)}个数值型字段，可进行量化分析。")
            
            # 查找异常值
            for col in numeric_cols[:3]:  # 只分析前3个数值列
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                outliers = df[(df[col] < q1 - 1.5*iqr) | (df[col] > q3 + 1.5*iqr)]
                if len(outliers) > 0:
                    outlier_ratio = len(outliers) / len(df) * 100
                    insights.append(f"字段'{col}'存在约{outlier_ratio:.1f}%的异常值，建议进一步核查。")
        
        # 日期时间列洞察
        date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        if date_cols:
            insights.append(f"数据包含{len(date_cols)}个时间序列字段，可进行趋势分析。")
        
        # AI增强分析（如果启用）
        if self.ai_analyzer and self.ai_analyzer.enabled:
            print(f"  -> 正在使用AI模型生成深度洞察...")
            data_summary = {
                '总行数': row_count,
                '总列数': col_count,
                '数值字段': numeric_cols,
                '缺失值总数': int(total_missing)
            }
            ai_insights = self.ai_analyzer.analyze_data_insights(
                data_summary, 
                analysis['file_name']
            )
            if ai_insights:
                insights.append("---AI智能分析---")
                insights.extend(ai_insights)
        
        analysis['insights'] = insights
    
    def analyze_all_files(self):
        """分析所有数据文件"""
        if not self.data_files:
            self.scan_data_files()
        
        if not self.data_files:
            print("警告：未找到任何数据文件！")
            return None
        
        print("\n开始分析数据...")
        for file_path in self.data_files:
            file_name = os.path.basename(file_path)
            print(f"正在分析: {file_name}")
            
            df = self.load_data(file_path)
            if df is not None:
                analysis = self.analyze_dataframe(df, file_name)
                self.analysis_results[file_name] = analysis
            else:
                print(f"跳过文件: {file_name}")
        
        print(f"\n分析完成！共分析了 {len(self.analysis_results)} 个文件")
        return self.analysis_results
    
    def create_html_report(self):
        """创建HTML分析报告"""
        print("\n正在生成HTML报告...")
        
        # HTML模板头部
        html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>金融数据分析报告</title>
    <style>
        body {
            font-family: "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
            line-height: 1.8;
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 20px;
            font-size: 36px;
        }
        h2 {
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 28px;
            border-left: 5px solid #3498db;
            padding-left: 15px;
        }
        h3 {
            color: #555;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 22px;
        }
        h4 {
            color: #666;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 18px;
            background-color: #ecf0f1;
            padding: 10px;
            border-radius: 5px;
        }
        .timestamp {
            text-align: center;
            color: #7f8c8d;
            font-size: 16px;
            margin-bottom: 30px;
        }
        .section {
            margin: 30px 0;
            padding: 20px;
            background-color: #fafafa;
            border-radius: 8px;
        }
        .insight-box {
            background-color: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }
        .warning-box {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }
        .info-box {
            background-color: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }
        ul {
            line-height: 2;
        }
        li {
            margin: 10px 0;
        }
        .stats-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
        }
        .stats-table th {
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
        }
        .stats-table td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        .stats-table tr:hover {
            background-color: #f5f5f5;
        }
        .file-section {
            margin-top: 50px;
            padding-top: 30px;
            border-top: 2px dashed #bdc3c7;
        }
        .highlight {
            background-color: #fff9c4;
            padding: 2px 5px;
            border-radius: 3px;
        }
        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #95a5a6;
        }
    </style>
</head>
<body>
    <div class="container">
"""
        
        # 标题和时间
        html_content += f"""
        <h1>[STAT] 金融数据分析报告</h1>
        <div class="timestamp">报告生成时间: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}</div>
"""
        
        # 概述部分
        html_content += """
        <h2>一、分析概述</h2>
"""
        
        if not self.analysis_results:
            html_content += """
        <div class="warning-box">
            <strong>[WARN] 提示：</strong>未找到可分析的数据文件。请确保金融数据文件夹中包含CSV、Excel或TXT格式的数据文件。
        </div>
"""
        else:
            html_content += f"""
        <div class="info-box">
            <p><strong>[FILE] 数据文件数量：</strong>{len(self.analysis_results)}个</p>
            <p>通俗地说，我们就像给这些数据做了一次全面"体检"，从各个角度检查数据的健康状况。</p>
        </div>
        
        <h3>📖 专业术语解释</h3>
        <ul>
            <li><strong>描述性统计：</strong>用数字概括数据的基本特征，如平均值、中位数等</li>
            <li><strong>分位数：</strong>将数据从小到大排列后的位置点，如25%分位数表示有25%的数据小于该值</li>
            <li><strong>标准差：</strong>衡量数据波动程度的指标，值越大说明数据越分散</li>
            <li><strong>异常值：</strong>与大多数数据差异较大的特殊值，可能是错误数据或极端情况</li>
        </ul>
"""
        
        # 为每个文件添加详细分析
        for idx, (file_name, analysis) in enumerate(self.analysis_results.items(), 1):
            basic_info = analysis['basic_info']
            
            html_content += f"""
        <div class="file-section">
            <h2>{idx}、{file_name} 分析报告</h2>
            
            <h3>1.1 数据基本信息</h3>
            <div class="section">
                <h4>[STAT] 数据规模</h4>
                <p>这个文件包含 <span class="highlight">{basic_info['总行数']}</span> 条数据记录和 <span class="highlight">{basic_info['总列数']}</span> 个数据字段。</p>
                <p>用大白话讲，就是有 <strong>{basic_info['总行数']}</strong> 行数据，每行数据有 <strong>{basic_info['总列数']}</strong> 个不同的信息项。</p>
                
                <h4>[NOTE] 字段列表</h4>
                <p>数据包含以下字段：{', '.join(basic_info['列名'][:10])}{'...' if len(basic_info['列名']) > 10 else ''}</p>
            </div>
"""
            
            # 缺失值分析
            missing_data = basic_info['缺失值数量']
            has_missing = any(v > 0 for v in missing_data.values())
            
            if has_missing:
                html_content += """
            <h3>1.2 数据完整性分析</h3>
            <div class="warning-box">
                <h4>[WARN] 缺失值情况</h4>
                <p>简单来说，就是有些地方的数据是空的，没有记录。这可能影响分析的准确性。</p>
                <ul>
"""
                for col, count in missing_data.items():
                    if count > 0:
                        ratio = (count / basic_info['总行数']) * 100
                        html_content += f"                    <li><strong>{col}:</strong> 缺失{count}个值，占比{ratio:.2f}%</li>\n"
                
                html_content += """
                </ul>
            </div>
"""
            
            # 统计分析
            if analysis['statistical_summary'].get('数值列'):
                html_content += """
            <h3>1.3 数值统计分析</h3>
            <div class="info-box">
                <h4>[UP] 统计指标解读</h4>
                <p>下面是各个数值字段的统计分析。我们用多个指标来全面了解数据的特点：</p>
                <ul>
                    <li><strong>均值：</strong>所有数据的平均值，代表数据的中心水平</li>
                    <li><strong>中位数：</strong>排序后位于中间的值，不受极端值影响</li>
                    <li><strong>标准差：</strong>数据的波动幅度，值越大说明数据越不稳定</li>
                    <li><strong>最小值/最大值：</strong>数据的范围边界</li>
                </ul>
            </div>
"""
                
                for col, stats in analysis['statistical_summary']['数值列'].items():
                    volatility = '较大' if stats['标准差'] > stats['均值'] * 0.5 else '适中'
                    range_val = stats['最大值'] - stats['最小值']
                    
                    html_content += f"""
            <div class="section">
                <h4>[STAT] {col}</h4>
                <table class="stats-table">
                    <tr>
                        <th>指标</th>
                        <th>数值</th>
                        <th>说明</th>
                    </tr>
                    <tr>
                        <td>平均值</td>
                        <td>{stats['均值']:.4f}</td>
                        <td>数据的中心水平</td>
                    </tr>
                    <tr>
                        <td>中位数</td>
                        <td>{stats['中位数']:.4f}</td>
                        <td>排序后的中间值</td>
                    </tr>
                    <tr>
                        <td>标准差</td>
                        <td>{stats['标准差']:.4f}</td>
                        <td>波动程度指标</td>
                    </tr>
                    <tr>
                        <td>最小值</td>
                        <td>{stats['最小值']:.4f}</td>
                        <td>数据下限</td>
                    </tr>
                    <tr>
                        <td>最大值</td>
                        <td>{stats['最大值']:.4f}</td>
                        <td>数据上限</td>
                    </tr>
                    <tr>
                        <td>25%分位数</td>
                        <td>{stats['25%分位数']:.4f}</td>
                        <td>较低水平</td>
                    </tr>
                    <tr>
                        <td>75%分位数</td>
                        <td>{stats['75%分位数']:.4f}</td>
                        <td>较高水平</td>
                    </tr>
                </table>
                <p><strong>[IDEA] 白话解读：</strong>这个字段的平均水平在<span class="highlight">{stats['均值']:.2f}</span>左右，
                数据波动<strong>{volatility}</strong>，
                最低和最高值相差<span class="highlight">{range_val:.2f}</span>。</p>
            </div>
"""
            
            # 洞察与建议
            if analysis['insights']:
                html_content += """
            <h3>1.4 数据洞察与建议</h3>
            <div class="insight-box">
                <h4>[FIND] 关键发现</h4>
                <p>通过对数据的深入分析，我们发现以下值得关注的情况：</p>
                <ul>
"""
                for insight in analysis['insights']:
                    html_content += f"                    <li>{insight}</li>\n"
                
                html_content += """
                </ul>
            </div>
"""
            
            html_content += """
        </div>
"""
        
        # 总结部分
        if self.analysis_results:
            html_content += f"""
        <div class="file-section">
            <h2>二、总体结论</h2>
            
            <div class="insight-box">
                <h3>[LIST] 分析总结</h3>
                <p>本次数据分析工作已经完成，共对<strong>{len(self.analysis_results)}</strong>个数据文件进行了全面的统计分析。</p>
                
                <h4>[TGT] 从专业角度来看，我们进行了以下分析工作：</h4>
                <ol>
                    <li><strong>描述性统计分析：</strong>计算了各项数据的中心趋势和离散程度</li>
                    <li><strong>数据质量评估：</strong>检查了数据的完整性和异常值情况</li>
                    <li><strong>分布特征分析：</strong>通过分位数了解数据的分布特点</li>
                </ol>
                
                <h4>[CHAT] 用大白话总结：</h4>
                <p>我们像给数据做了一次"全身体检"，不仅看了数据的"身高体重"（均值、总数），
                还查看了数据的"健康状况"（有没有缺失、有没有异常），
                以及数据的"稳定性"（波动大不大）。</p>
            </div>
            
            <div class="info-box">
                <h3>[IDEA] 后续建议</h3>
                <ol>
                    <li>对于缺失值较多的字段，建议补充数据或使用插值方法处理</li>
                    <li>对于存在异常值的字段，建议核实数据来源和准确性</li>
                    <li>可以根据业务需求进行更深入的相关性分析或趋势预测</li>
                </ol>
                <p><em>注：本报告基于现有数据生成，具体业务结论需结合实际情况判断。</em></p>
            </div>
        </div>
"""
        
        # HTML结尾
        html_content += """
        <div class="footer">
            <p>—— 报告结束 ——</p>
            <p>本报告由金融数据分析系统自动生成</p>
        </div>
    </div>
</body>
</html>
"""
        
        # 保存HTML文件
        output_file = os.path.join(self.output_path, f'金融数据分析报告_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"报告已生成: {output_file}")
        print("提示：双击HTML文件即可在浏览器中打开查看")
        return output_file


def main():
    """主程序"""
    print("=" * 60)
    print("金融数据分析系统 (AI增强版)".center(60))
    print("=" * 60)
    
    # 设置路径
    data_path = r"C:\Users\Edson\code\.vscode\量化交易\金融数据"
    output_path = r"C:\Users\Edson\code\.vscode\量化交易\分析数据"
    
    # AI配置 - 用户可以根据需求修改
    print("\n[BOT] AI模型配置")
    print("-" * 60)
    enable_ai = input("是否启用AI增强分析？(y/n，默认n): ").strip().lower() == 'y'
    
    ai_config = None
    if enable_ai:
        print("\n请选择AI模型类型:")
        print("1. Ollama (本地运行，推荐)")
        print("2. OpenAI兼容API (如LM Studio、vLLM等)")
        print("3. 不使用AI")
        
        choice = input("请输入选择 (1-3，默认1): ").strip() or '1'
        
        if choice == '1':
            model_name = input("Ollama模型名称 (默认: llama2): ").strip() or 'llama2'
            api_url = input("API地址 (默认: http://localhost:11434/api/generate): ").strip() or None
            ai_config = {
                'model_type': 'ollama',
                'model_name': model_name,
                'api_url': api_url
            }
        elif choice == '2':
            model_name = input("模型名称: ").strip() or 'gpt-3.5-turbo'
            api_url = input("API地址: ").strip()
            ai_config = {
                'model_type': 'openai_compatible',
                'model_name': model_name,
                'api_url': api_url
            }
        else:
            enable_ai = False
    
    print("\n" + "=" * 60)
    
    # 创建分析器实例
    analyzer = FinancialDataAnalyzer(data_path, output_path, enable_ai=enable_ai, ai_config=ai_config)
    
    # 扫描并分析数据
    analyzer.scan_data_files()
    
    if not analyzer.data_files:
        print("\n⚠ 警告：金融数据文件夹中没有找到数据文件！")
        print(f"请在以下路径放入CSV、Excel或TXT格式的数据文件：")
        print(f"{data_path}")
        print("\n系统将生成一个示例报告以供参考...")
    
    analyzer.analyze_all_files()
    
    # 生成HTML报告
    report_file = analyzer.create_html_report()
    
    print("\n" + "=" * 60)
    print("分析完成！".center(60))
    print("=" * 60)
    print(f"\n报告保存位置: {report_file}")
    print("\n提示：如果需要分析数据，请将数据文件放入'金融数据'文件夹后重新运行程序。")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n程序运行出错: {str(e)}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...")
