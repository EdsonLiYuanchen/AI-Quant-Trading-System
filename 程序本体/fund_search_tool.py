"""
基金查询工具 - 帮助查找和验证基金信息
"""

import os
import sys
import akshare as ak

# 智能数据查询模块：自动识别名称/代码
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from 智能数据查询 import SmartDataClient
    _SMART = SmartDataClient()
except Exception:
    _SMART = None

def search_fund_by_code(code):
    """按代码查询基金"""
    print(f"\n{'='*60}")
    print(f"查询基金代码: {code}")
    print(f"{'='*60}")

    found = False

    # 1. 查询ETF基金
    try:
        etf_df = ak.fund_etf_spot_em()
        etf_info = etf_df[etf_df['基金代码'] == code]
        if not etf_info.empty:
            print("\n✓ [ETF基金]")
            print(f"  基金名称: {etf_info.iloc[0]['基金名称']}")
            print(f"  最新价: {etf_info.iloc[0]['最新价']}")
            print(f"  涨跌幅: {etf_info.iloc[0]['涨跌幅']}%")
            print(f"  成交量: {etf_info.iloc[0]['成交量']}")
            found = True

            # 查询净值走势
            try:
                nav_df = ak.fund_em_open_fund_info(fund=code, indicator="单位净值走势")
                if not nav_df.empty:
                    print(f"  最新净值: {nav_df.iloc[-1]['单位净值']}")
                    print(f"  净值日期: {nav_df.iloc[-1]['净值日期']}")
            except Exception as e:
                print(f"  净值查询失败: {e}")
    except Exception as e:
        print(f"\n✗ ETF查询失败: {e}")

    # 2. 查询开放式基金净值走势
    try:
        nav_df = ak.fund_em_open_fund_info(fund=code, indicator="单位净值走势")
        if not nav_df.empty:
            print(f"\n✓ [开放式基金 - 通过净值]")
            print(f"  最新净值: {nav_df.iloc[-1]['单位净值']}")
            print(f"  净值日期: {nav_df.iloc[-1]['净值日期']}")
            print(f"  累计净值: {nav_df.iloc[-1]['累计净值']}")

            # 尝试获取更多基金信息
            try:
                fund_scale = ak.fund_em_open_fund_info(fund=code, indicator="基金规模")
                if not fund_scale.empty:
                    print(f"  基金规模: {fund_scale.iloc[-1]['基金规模']}")
            except:
                pass

            found = True
    except Exception as e:
        print(f"\n✗ 开放式基金净值查询失败: {e}")

    if not found:
        print(f"\n✗ 未找到基金代码: {code}")
        print(f"\n[IDEA] 建议:")
        print(f"  1. 确认代码格式正确（6位数字）")
        print(f"  2. 去掉代码前缀的0（如: 018124 -> 18124）")
        print(f"  3. 检查基金是否已清盘")
        print(f"  4. 在东方财富官网验证: https://fundf10.eastmoney.com/")
        print(f"  5. 尝试其他确认存在的基金: 159915, 510050, 000001")

    return found

def search_fund_by_name(name):
    """按名称搜索基金（智能识别：名称/代码/拼音都支持）"""
    print(f"\n{'='*60}")
    print(f"搜索基金名称: {name}")
    print(f"{'='*60}")

    # 智能解析优先（东财 codetable 接口，支持名称/代码/拼音）
    if _SMART is not None:
        try:
            syms = _SMART.resolve(name)
            if syms:
                funds = [s for s in syms if s.type == 'fund']
                if not funds:
                    funds = syms
                for i, s in enumerate(funds[:10]):
                    print(f"{i+1}. {s.code} - {s.name} [{s.type}]")
                return True
        except Exception:
            pass

    try:
        # 尝试获取热门基金列表
        try:
            etf_df = ak.fund_etf_spot_em()
            # 过滤包含名称的基金
            matched_funds = etf_df[etf_df['基金名称'].str.contains(name, case=False, na=False)]

            if not matched_funds.empty:
                print(f"\n找到 {len(matched_funds)} 只ETF/LOF基金:\n")

                # 按成交量排序
                matched_funds = matched_funds.sort_values('成交量', ascending=False)

                for i, (idx, row) in enumerate(matched_funds.iterrows()):
                    if i >= 10:
                        print(f"\n... 还有 {len(matched_funds) - 10} 只基金")
                        break

                    print(f"{i+1}. {row['基金代码']} - {row['基金名称']}")
                    print(f"   最新价: {row['最新价']:<8} 涨跌: {row['涨跌幅']:+>6}%")
                    print()

                return True
        except Exception as e:
            print(f"\n✗ ETF/LOF基金搜索失败: {e}")

        print(f"\n[IDEA] 提示: akshare暂不支持按名称搜索开放式基金")
        print(f"   建议:")
        print(f"   1. 使用确认存在的基金代码进行测试")
        print(f"   2. 在东方财富官网查找基金代码: https://fundf10.eastmoney.com/")
        print(f"   3. 使用以下热门基金代码测试:")
        print(f"      - 159915 (创业板ETF)")
        print(f"      - 510050 (上证50ETF)")
        print(f"      - 510300 (沪深300ETF)")
        print(f"      - 000001 (华夏成长混合)")

        return False

    except Exception as e:
        print(f"\n✗ 搜索失败: {e}")
        return False

def get_fund_list(fund_type='all', limit=20):
    """获取基金列表"""
    print(f"\n{'='*60}")
    print(f"基金列表 ({fund_type})")
    print(f"{'='*60}")

    try:
        if fund_type in ['etf', 'lof']:
            # 获取ETF/LOF基金
            df = ak.fund_etf_spot_em()
            print(f"\n共找到 {len(df)} 只基金\n")

            # 按成交量排序
            df = df.sort_values('成交量', ascending=False).head(limit)

            for i, row in df.iterrows():
                print(f"{i+1:2d}. {row['基金代码']} - {row['基金名称']}")
                print(f"     最新价: {row['最新价']:<8} 涨跌: {row['涨跌幅']:+>6}% 成交量: {row['成交量']}")
        else:
            # 获取开放式基金列表（需要搜索）
            print("\n开放式基金列表（按名称搜索）:")
            print("建议使用 '股票'、'混合'、'债券' 等关键词搜索\n")

        return True

    except Exception as e:
        print(f"\n✗ 获取失败: {e}")
        return False

def main():
    """主菜单"""
    print("="*60)
    print("        基金查询工具 v1.0")
    print("="*60)

    while True:
        print("\n【主菜单】")
        print("1. 按代码查询基金")
        print("2. 按名称搜索基金")
        print("3. 查看热门ETF基金")
        print("4. 查看热门LOF基金")
        print("5. 测试特定代码 (018124)")
        print("0. 退出")

        choice = input("\n请选择操作 (0-5): ").strip()

        if choice == '0':
            print("\n再见！")
            break
        elif choice == '1':
            code = input("请输入基金代码: ").strip()
            if code:
                search_fund_by_code(code)
        elif choice == '2':
            name = input("请输入基金名称或关键词: ").strip()
            if name:
                search_fund_by_name(name)
        elif choice == '3':
            get_fund_list('etf', limit=10)
        elif choice == '4':
            get_fund_list('lof', limit=10)
        elif choice == '5':
            # 测试018124
            search_fund_by_code('018124')
            print("\n尝试不同格式:")
            for code in ['018124', '18124', '018124.OF']:
                print(f"\n测试代码: {code}")
                search_fund_by_code(code)
        else:
            print("\n无效选择，请重新输入")

        input("\n按回车继续...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已退出")
    except Exception as e:
        print(f"\n程序出错: {e}")
