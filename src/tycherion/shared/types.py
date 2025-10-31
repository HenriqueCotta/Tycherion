from __future__ import annotations
from typing import TypedDict, Literal

class Tick(TypedDict):
    bid: float
    ask: float
    last: float
    time: int

Side = Literal["BUY", "SELL"]
