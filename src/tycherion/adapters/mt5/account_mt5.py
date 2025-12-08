from __future__ import annotations

import MetaTrader5 as mt5

from tycherion.ports.account import AccountPort
from tycherion.domain.portfolio.entities import Position


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

    def positions(self) -> list[Position]:
        poss = mt5.positions_get()
        out: list[Position] = []
        if poss:
            for p in poss:
                out.append(
                    Position(
                        symbol=p.symbol,
                        quantity=float(getattr(p, "volume", 0.0) or 0.0),
                        price=float(getattr(p, "price_open", 0.0) or 0.0),
                    )
                )
        return out
