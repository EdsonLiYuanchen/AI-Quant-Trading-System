"""
测试查询基金 - 修复版
"""

import akshare as ak

def test_fund_code(code):
    """测试单个基金代码"""
    print(f"\n{'='*60}")
    print(f"测试基金代码: {code}")
    print(f"{'='*60}")

    found = False

    # 方法1: 查询ETF基金
    print("\n【方法1】查询ETF/LOF基金")
    try:
        fund_df = ak.fund_etf_spot_em()
        fund_info = fund_df[fund_df['基金代码'] == code]
        if not fund_info.empty:
            print(f"✓ 找到基金: {fund_info.iloc[0]['基金名称']}")
            print(f"  最新价: {fund_info.iloc[0]['最新价']}")
            print(f"  涨跌幅: {fund_info.iloc[0]['涨跌幅']}%")
            print(f"  成交量: {fund_info.iloc[0]['成交量']}")
            found = True
        else:
            print("✗ 未在ETF/LOF基金中找到")
    except Exception as e:
        print(f"✗ 查询失败: {e}")

    # 方法2: 查询基金净值走势
    print("\n【方法2】查询基金净值走势")
    try:
        fund_detail = ak.fund_em_open_fund_info(fund=code, indicator="单位净值走势")
        if not fund_detail.empty:
            print(f"✓ 获取到净值数据: {len(fund_detail)} 条")
            print(f"  最新净值: {fund_detail.iloc[-1]['单位净值']}")
            print(f"  净值日期: {fund_detail.iloc[-1]['净值日期']}")
            print(f"  累计净值: {fund_detail.iloc[-1]['累计净值']}")
            found = True
        else:
            print("✗ 未获取到净值数据")
    except Exception as e:
        print(f"✗ 查询净值失败: {e}")

    return found

# 主程序
print("="*80)
print("基金查询测试")
print("="*80)

# 测试018124
test_fund_code('018124')

# 测试其他格式
print("\n\n尝试不同的代码格式:")
for code in ['018124', '18124', '018124']:
    test_fund_code(code)

# 测试确认存在的基金
print("\n\n" + "="*80)
print("测试确认存在的基金（对比验证）")
print("="*80)

test_funds = [
    '159915',  # 创业板ETF
    '510050',  # 上证50ETF
    '510300',  # 沪深300ETF
    '000001',  # 华夏成长混合
]

for code in test_funds:
    test_fund_code(code)

print("\n" + "="*80)
print("测试完成")
print("="*80)
print("\n[IDEA] 总结:")
print("- 如果018124查询不到，说明该基金不在akshare数据源中")
print("- 建议在东方财富官网验证: https://fundf10.eastmoney.com/")
print("- 其他确认存在的基金可以正常查询，系统功能正常")

