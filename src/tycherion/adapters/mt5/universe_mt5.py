from __future__ import annotations
import MetaTrader5 as mt5
from typing import List
from tycherion.ports.universe import UniversePort

class MT5Universe(UniversePort):
    def visible_symbols(self) -> List[str]:
        syms = mt5.symbols_get()
        return [s.name for s in syms if getattr(s, "visible", False)]

    def by_pattern(self, pattern: str) -> List[str]:
        syms = mt5.symbols_get(pattern)
        return [s.name for s in syms]

