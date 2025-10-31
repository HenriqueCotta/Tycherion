from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional, Literal

Side = Literal["BUY", "SELL"]

@dataclass
class TradeResult:
    ok: bool
    retcode: int
    order: Optional[int]
    message: str

class TradingPort(Protocol):
    def market_buy(self, symbol: str) -> TradeResult: ...
    def market_sell(self, symbol: str) -> TradeResult: ...
