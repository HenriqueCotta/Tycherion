from __future__ import annotations
import MetaTrader5 as mt5
from tycherion.ports.account import AccountPort, Position

class MT5Account(AccountPort):
    def is_demo(self) -> bool:
        ai = mt5.account_info()
        return bool(ai and ai.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO)

    def balance(self) -> float:
        ai = mt5.account_info()
        return float(getattr(ai, "balance", 0.0) or 0.0)

    def equity(self) -> float:
        ai = mt5.account_info()
        return float(getattr(ai, "equity", 0.0) or 0.0)

    def positions(self):
        poss = mt5.positions_get()
        out = []
        if poss:
            for p in poss:
                out.append(Position(symbol=p.symbol, volume=float(p.volume or 0.0), price=float(p.price_open or 0.0)))
        return out
