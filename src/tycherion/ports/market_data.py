from __future__ import annotations
from typing import Protocol
from datetime import datetime
import pandas as pd

class MarketDataPort(Protocol):
    def get_bars(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame: ...
