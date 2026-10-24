"""
尝试从同花顺网站提取数据
"""

import requests
from bs4 import BeautifulSoup
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Referer': 'https://www.10jqka.com.cn/',
}

def test_ths_html():
    """测试从同花顺HTML页面提取数据"""
    print("="*80)
    print("🧪 测试同花顺HTML页面")
    print("="*80)
    
    urls = [
        {
            'name': '同花顺概念板块',
            'url': 'https://q.10jqka.com.cn/gn/'
        },
        {
            'name': '同花顺A股行情',
            'url': 'https://q.10jqka.com.cn/'
        },
        {
            'name': '同花顺首页',
            'url': 'https://www.10jqka.com.cn/'
        },
    ]
    
    for info in urls:
        print(f"\n【测试】{info['name']}")
        print(f"URL: {info['url']}")
        
        try:
            session = requests.Session()
            session.verify = False
            session.headers.update(headers)
            
            response = session.get(info['url'], timeout=30)
            
            if response.status_code == 200:
                print(f"[OK] 连接成功")
                print(f"响应长度: {len(response.text)} bytes")
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找表格数据
                tables = soup.find_all('table')
                print(f"找到 {len(tables)} 个表格")
                
                # 查找脚本数据（通常在script标签中）
                scripts = soup.find_all('script')
                print(f"找到 {len(scripts)} 个脚本标签")
                
                # 查找包含股票数据的脚本
                for i, script in enumerate(scripts[:3]):
                    if script.string and ('gnData' in script.string or 'stockList' in script.string or 'data' in script.string.lower()):
                        print(f"脚本 {i+1}: 可能包含数据，长度 {len(script.string[:200]) if script.string else 0}")
                
            else:
                print(f"[ERROR] HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"[ERROR] 错误: {e}")
            
        time.sleep(2)

if __name__ == "__main__":
    test_ths_html()