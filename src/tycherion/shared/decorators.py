from __future__ import annotations
from functools import wraps
import MetaTrader5 as mt5

def demo_only(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        require = getattr(self, "require_demo", True)
        if require:
            ai = mt5.account_info()
            if not ai or ai.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
                raise RuntimeError("Blocked: only allowed in DEMO account.")
        return fn(self, *args, **kwargs)
    return wrapper

def logged(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        name = fn.__qualname__
        try:
            res = fn(*args, **kwargs)
            print(f"{name}: ok -> {res}")
            return res
        except Exception as e:
            print(f"{name}: error -> {e}")
            raise
    return wrapper

