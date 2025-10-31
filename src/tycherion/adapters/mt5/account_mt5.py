from __future__ import annotations
import MetaTrader5 as mt5
from tycherion.ports.account import AccountPort

class MT5Account(AccountPort):
    def is_demo(self) -> bool:
        ai = mt5.account_info()
        return bool(ai and ai.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO)
