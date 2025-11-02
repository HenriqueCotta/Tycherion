from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict
import pandas as pd
import MetaTrader5 as mt5
from tycherion.ports.market_data import MarketDataPort

_TF_MAP: Dict[str, int] = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

class MT5MarketData(MarketDataPort):
    def get_bars(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
        timeFrame = _TF_MAP.get(timeframe.upper())
        if timeFrame is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        rates = mt5.copy_rates_range(
            symbol, timeFrame,
            start.astimezone(timezone.utc),
            end.astimezone(timezone.utc)
        )
        if rates is None or len(rates) == 0:
            return pd.DataFrame(columns=[
                "time","open","high","low","close","tick_volume","spread","real_volume"
            ])
        dataFrame = pd.DataFrame(rates)
        dataFrame["time"] = pd.to_datetime(dataFrame["time"], unit="s", utc=True)
        return dataFrame
