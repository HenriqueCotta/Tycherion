from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, List

@dataclass
class Position:
    symbol: str
    volume: float
    price: float

class AccountPort(Protocol):
    def is_demo(self) -> bool: ...
    def balance(self) -> float: ...
    def equity(self) -> float: ...
    def positions(self) -> List[Position]: ...
