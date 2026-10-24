"""
自选股管理模块
提供自选股列表的持久化存储（watchlist.json）与增删查。
"""

import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

WATCHLIST_FILE = 'watchlist.json'


class Watchlist:
    """自选股列表（持久化到 watchlist.json）"""

    def __init__(self, filepath=WATCHLIST_FILE):
        self.filepath = filepath
        self.items = []  # [{'code','name','add_time','remark'}]
        self._load()

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

    def _save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存自选股失败: {e}")

    def all(self):
        return list(self.items)

    def has(self, code):
        code = self._norm(code)
        return any(self._norm(i.get('code', '')) == code for i in self.items)

    def add(self, code, name=''):
        """添加一只自选股，返回 (ok, msg)"""
        code = self._norm(code)
        if not code:
            return False, '代码为空'
        if self.has(code):
            return False, f'{code} 已在自选股中'
        self.items.append({
            'code': code,
            'name': name or code,
            'add_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'remark': '',
        })
        self._save()
        return True, f'已添加 {code} {name} 到自选股'

    def add_many(self, pairs):
        """批量添加，pairs=[(code,name),...]，返回 (成功数, 已存在数, 失败列表)"""
        ok = 0
        dup = 0
        failed = []
        for code, name in pairs:
            s, _ = self.add(code, name)
            if s:
                ok += 1
            elif self.has(code):
                dup += 1
            else:
                failed.append(code)
        return ok, dup, failed

    def remove(self, code):
        code = self._norm(code)
        before = len(self.items)
        self.items = [i for i in self.items if self._norm(i.get('code', '')) != code]
        if len(self.items) != before:
            self._save()
            return True, f'已移除 {code}'
        return False, f'{code} 不在自选股中'

    def remove_all(self):
        self.items = []
        self._save()
        return True, '已清空自选股'

    @staticmethod
    def _norm(code):
        return str(code or '').strip().zfill(6)


def _demo():
    wl = Watchlist()
    print(wl.add('600519', '贵州茅台'))
    print(wl.add('600519', '贵州茅台'))
    print(wl.all())
    print(wl.remove('600519'))
    print(wl.all())


if __name__ == '__main__':
    _demo()
