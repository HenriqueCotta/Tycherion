from __future__ import annotations
import pandas as pd

def sma_cross_signal(df: pd.DataFrame, fast: int, slow: int) -> str:
    if df.empty or len(df) < max(fast, slow):
        return "HOLD"
    df["sma_fast"] = df["close"].rolling(fast).mean()
    df["sma_slow"] = df["close"].rolling(slow).mean()
    last_fast = df["sma_fast"].iloc[-1]
    last_slow = df["sma_slow"].iloc[-1]
    if pd.isna(last_fast) or pd.isna(last_slow):
        return "HOLD"
    if last_fast > last_slow:
        return "BUY"
    if last_fast < last_slow:
        return "EXIT"
    return "HOLD"
