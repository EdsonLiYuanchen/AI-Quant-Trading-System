# -*- coding: utf-8 -*-
# akshare/utils stub
class _Demjson:
    """尽可能兼容 demjson.decode 的 JSON 解析接口。"""
    @staticmethod
    def decode(s, *args, **kwargs):
        s = s if isinstance(s, str) else s.decode('utf-8')
        try:
            return __import__('json').loads(s)
        except Exception:
            # demjson 允许单引号/松散引号；做一次容错
            import re
            fixed = re.sub(r"(?<![\w])'([^']*)'(?=\s*:)", r'"\1"', s)
            fixed = re.sub(r"(?<![\w])'([^']*)'(?=[,\]\s}])", r'"\1"', fixed)
            return __import__('json').loads(fixed)

    @staticmethod
    def encode(obj):
        return __import__('json').dumps(obj, ensure_ascii=False)


demjson = _Demjson()

__all__ = ["demjson"]
