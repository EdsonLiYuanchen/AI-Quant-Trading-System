"""打包版(console=False) sys.stdout/stderr 为 None 时的兜底保护。

PyInstaller 以 console=False 打包时 sys.stdout/sys.stderr 是 None，
akshare 内部 tqdm 等写 stdout 会报 AttributeError。调用 akshare 前先 ensure_streams()。
"""
import sys as _sys


class _Null:
    """无害输出对象：write/flush 均不做事。"""

    def write(self, s):
        pass

    def flush(self):
        pass


def ensure_streams() -> bool:
    """若 sys.stdout/stderr 为 None 则替换为无害对象，返回是否改动过。"""
    changed = False
    if _sys.stdout is None:
        _sys.stdout = _Null()
        changed = True
    if _sys.stderr is None:
        _sys.stderr = _Null()
        changed = True
    return changed
