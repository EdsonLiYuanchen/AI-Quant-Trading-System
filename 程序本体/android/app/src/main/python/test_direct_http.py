"""
直接使用HTTP请求测试数据接口，绕过akshare封装
"""

import requests
import time
import json

# 模拟浏览器请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Origin': 'https://quote.eastmoney.com',
    'Referer': 'https://quote.eastmoney.com/',
}

def test_eastmoney_api():
    """测试东方财富API"""
    print("="*80)
    print("🧪 测试东方财富API")
    print("="*80)
    
    # 东方财富股票行情接口
    urls = [
        {
            'name': '东方财富A股行情',
            'url': 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&wbp2u=|0|0|0|web&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152',
            'timeout': 30
        },
        {
            'name': '东方财富上证指数',
            'url': 'https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f57,f58,f116,f117,f118,f174,f175,f59,f168,f169,f170,f171,f173,f172,f100,f101,f102,f103,f104,f105,f106,f107,f108,f109,f110,f111,f112,f113,f114,f115,f120,f121,f122,f123,f124,f125,f92,f93,f94,f95,f96,f97,f98,f99,f252,f253,f254,f255,f256,f257,f258,f259,f260,f261,f262,f263,f264,f265,f266,f267,f268,f269,f270,f271,f272,f273,f274,f275,f276,f277,f278,f279,f280,f281,f282,f283,f284,f285,f286,f287,f288,f289,f290,f291,f292,f293,f294,f295,f296,f297,f298,f299,f300,f301,f302,f303,f304,f305,f306,f307,f308,f309,f310,f311,f312,f313,f314,f315,f316,f317,f318,f319,f320,f321,f322,f323,f324,f325,f326,f327,f328,f329,f330,f331,f332,f333,f334,f335,f336,f337,f338,f339,f340,f341,f342,f343,f344,f345,f346,f347,f348,f349,f350,f351,f352,f353,f354,f355,f356,f357,f358,f359,f360,f361,f362,f363,f364,f365,f366,f367,f368,f369,f370,f371,f372,f373,f374,f375,f376,f377,f378,f379,f380,f381,f382,f383,f384,f385,f386,f387,f388,f389,f390',
            'timeout': 30
        },
        {
            'name': '同花顺概念板块',
            'url': 'https://q.10jqka.com.cn/gn/',
            'timeout': 30
        },
    ]
    
    for info in urls:
        print(f"\n【测试】{info['name']}")
        print(f"URL: {info['url'][:60]}...")
        
        try:
            session = requests.Session()
            session.verify = False
            session.headers.update(headers)
            
            start_time = time.time()
            response = session.get(info['url'], timeout=info['timeout'])
            elapsed = time.time() - start_time
            
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {elapsed:.2f}s")
            print(f"响应长度: {len(response.text)} bytes")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"[OK] JSON解析成功")
                    if isinstance(data, dict):
                        print(f"   键: {list(data.keys())[:5]}...")
                except json.JSONDecodeError:
                    print(f"[WARN] 非JSON响应，前200字符: {response.text[:200]}...")
            else:
                print(f"[ERROR] HTTP错误: {response.status_code}")
                
        except requests.exceptions.ConnectionError as e:
            print(f"[ERROR] 连接错误: {e}")
        except requests.exceptions.Timeout as e:
            print(f"[ERROR] 请求超时: {e}")
        except Exception as e:
            print(f"[ERROR] 未知错误: {e}")
            
        time.sleep(2)

if __name__ == "__main__":
    test_eastmoney_api()