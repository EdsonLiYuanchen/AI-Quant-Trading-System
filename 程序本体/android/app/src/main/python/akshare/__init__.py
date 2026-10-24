# -*- coding: utf-8 -*-
"""
akshare stub for Android (Chaquopy).
akshare 官方暂无 Android wheel。本 stub 让所有 `import akshare` 顺利通过，
并提供一个可工作的 `utils.demjson.decode`（用于新浪接口直接解析）；
其它 ak.* 接口调用抛出异常，上层已有的 try/except 会自动降级到
新浪/东财直连。 —— 仅为保持完整功能链路在安卓可 import 而做的最小实现。
"""
import json as _json


def _unavailable(name):
    raise RuntimeError("akshare在本平台不可用（安卓）: %s" % name)


class _AK:
    """任何属性访问返回一个会抛异常的调用体，对已有的 except 降级逻辑友好。"""

    def __getattr__(self, name):
        def fn(*args, **kwargs):
            _unavailable(name)
        return fn


# 供 `if ak is not None:` 风格判断 — 保持非空以不跳过降级逻辑
ak = _AK()

# 常用函数别名（顶层调用形式 ak.stock_zh_a_spot_em() 等）
stock_zh_a_spot_em = lambda *a, **k: _unavailable("stock_zh_a_spot_em")
stock_zh_a_spot = lambda *a, **k: _unavailable("stock_zh_a_spot")
stock_info_a_code_name = lambda *a, **k: _unavailable("stock_info_a_code_name")
stock_hk_spot = lambda *a, **k: _unavailable("stock_hk_spot")
stock_zh_a_daily = lambda *a, **k: _unavailable("stock_zh_a_daily")
stock_zh_a_hist = lambda *a, **k: _unavailable("stock_zh_a_hist")
stock_zh_index_spot_em = lambda *a, **k: _unavailable("stock_zh_index_spot_em")
stock_board_spot_em = lambda *a, **k: _unavailable("stock_board_spot_em")
stock_zh_a_hist_min_em = lambda *a, **k: _unavailable("stock_zh_a_hist_min_em")


class _UtilsModule:
    pass


from .utils import demjson  # noqa: E402,F401  供 `from akshare.utils import demjson`
