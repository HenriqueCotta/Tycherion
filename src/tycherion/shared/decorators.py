from __future__ import annotations
from functools import wraps
import logging
import MetaTrader5 as mt5

_log = logging.getLogger(__name__)

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
            _log.debug("%s: ok -> %s", name, res)
            return res
        except Exception as e:
            _log.exception("%s: error", name)
            raise
    return wrapper
