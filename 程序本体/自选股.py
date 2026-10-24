"""
自选股管理模块
提供自选股列表的持久化存储（watchlist.json）与增删查。
支持 A 股（默认）/ 港股 / 美股，市场字段 market ∈ {'a','hk','us'}。
旧数据（无 market 字段）自动视为 A 股，向后兼容。
"""

import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

WATCHLIST_FILE = 'watchlist.json'

# 合法市场标识
VALID_MARKETS = ('a', 'hk', 'us')
MARKET_NAMES = {'a': 'A股', 'hk': '港股', 'us': '美股'}


class Watchlist:
    """自选股列表（持久化到 watchlist.json）

    每条记录字段：
      code       股票代码（A股6位数字 / 港股5位数字 / 美股字母ticker）
      name       股票名称
      market     'a' / 'hk' / 'us'（默认 'a'，兼容旧数据）
      add_time   添加时间
      remark     备注
    """

    def __init__(self, filepath=WATCHLIST_FILE):
        self.filepath = filepath
        self.items = []  # [{'code','name','market','add_time','remark'}]
        self._load()

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def _load(self):
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.items = data
                    elif isinstance(data, dict) and isinstance(data.get('items'), list):
                        self.items = data['items']
        except Exception:
            self.items = []
        # 兼容旧数据：没有 market 字段的记录补 'a'
        for it in self.items:
            if it.get('market') not in VALID_MARKETS:
                it['market'] = 'a'

    def _save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存自选股失败: {e}")

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def all(self):
        return list(self.items)

    def by_market(self, market):
        """按市场筛选。market: 'a' / 'hk' / 'us' / ''(全部)"""
        if not market or market not in VALID_MARKETS:
            return list(self.items)
        return [i for i in self.items if i.get('market') == market]

    def codes_by_market(self, market):
        return [i['code'] for i in self.by_market(market)]

    def has(self, code, market='a'):
        """判断某市场下的代码是否已在自选。A股按6位归一，港美股原样比较。"""
        code = self._norm_code(code, market)
        for i in self.items:
            if i.get('market', 'a') == market and \
               self._norm_code(i.get('code', ''), market) == code:
                return True
        return False

    # ------------------------------------------------------------------
    # 增删
    # ------------------------------------------------------------------
    def add(self, code, name='', market='a'):
        """添加一只自选股，返回 (ok, msg)。market 默认 'a'。"""
        market = market if market in VALID_MARKETS else 'a'
        code = self._norm_code(code, market)
        if not code:
            return False, '代码为空'
        if self.has(code, market):
            return False, f'{code} 已在自选股中（{MARKET_NAMES[market]}）'
        self.items.append({
            'code': code,
            'name': name or code,
            'market': market,
            'add_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'remark': '',
        })
        self._save()
        return True, f'已添加 {code} {name}（{MARKET_NAMES[market]}）到自选股'

    def add_many(self, pairs):
        """批量添加，pairs=[(code,name) 或 (code,name,market)]，
        返回 (成功数, 已存在数, 失败列表)"""
        ok = 0
        dup = 0
        failed = []
        for p in pairs:
            code = p[0]
            name = p[1] if len(p) > 1 else ''
            market = p[2] if len(p) > 2 else 'a'
            s, _ = self.add(code, name, market)
            if s:
                ok += 1
            elif self.has(code, market):
                dup += 1
            else:
                failed.append(code)
        return ok, dup, failed

    def remove(self, code, market='a'):
        market = market if market in VALID_MARKETS else 'a'
        code = self._norm_code(code, market)
        before = len(self.items)
        self.items = [i for i in self.items
                      if not (i.get('market', 'a') == market and
                              self._norm_code(i.get('code', ''), market) == code)]
        if len(self.items) != before:
            self._save()
            return True, f'已移除 {code}（{MARKET_NAMES[market]}）'
        return False, f'{code} 不在自选股中'

    def remove_all(self, market=''):
        """清空。market: 'a'/'hk'/'us' 或 ''(全部)。"""
        if market in VALID_MARKETS:
            self.items = [i for i in self.items if i.get('market') != market]
            self._save()
            return True, f'已清空{MARKET_NAMES[market]}自选股'
        self.items = []
        self._save()
        return True, '已清空自选股'

    # ------------------------------------------------------------------
    # 代码归一
    # ------------------------------------------------------------------
    @staticmethod
    def _norm_code(code, market='a'):
        code = str(code or '').strip()
        if not code:
            return code
        if market in ('hk',):
            # 港股：5位数字，允许带前缀
            digits = ''.join(ch for ch in code if ch.isdigit())
            return digits.zfill(5) if digits else code.upper()
        if market in ('us',):
            return code.upper()
        # A股：6位
        return code.zfill(6)


def _demo():
    wl = Watchlist()
    print(wl.add('600519', '贵州茅台', 'a'))
    print(wl.add('00700', '腾讯控股', 'hk'))
    print(wl.add('AAPL', '苹果', 'us'))
    print(wl.all())
    print('A股:', [i['code'] for i in wl.by_market('a')])
    print('港股:', [i['code'] for i in wl.by_market('hk')])
    print('美股:', [i['code'] for i in wl.by_market('us')])


if __name__ == '__main__':
    _demo()
