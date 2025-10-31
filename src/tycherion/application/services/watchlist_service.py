from __future__ import annotations
from datetime import datetime, timedelta, timezone
import pandas as pd
from typing import Sequence

from tycherion.shared.config import AppConfig
from tycherion.ports.market_data import MarketDataPort
from tycherion.ports.watchlist import WatchlistPort

def build_watchlist(cfg: AppConfig, data: MarketDataPort, provider: WatchlistPort) -> list[str]:
    mode = cfg.application.watchlist.mode
    if mode == "static":
        base = list(dict.fromkeys(cfg.application.watchlist.symbols or []))
    elif mode == "market_watch":
        base = provider.visible_symbols()
    elif mode == "pattern":
        patt = cfg.application.watchlist.pattern or "*"
        base = provider.by_pattern(patt)
    else:
        base = [cfg.symbol]

    top_n = cfg.application.watchlist.top_n or 0
    if top_n <= 0 or len(base) <= top_n:
        return base

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(cfg.lookback_days, 15))

    scores: list[tuple[float, str]] = []
    for sym in base[:200]:
        try:
            df = data.get_bars(sym, cfg.timeframe, start, end)
            if df.empty:
                score = 0.0
            else:
                score = float(pd.to_numeric(df["tick_volume"], errors="coerce").fillna(0).tail(100).mean())
        except Exception:
            score = 0.0
        scores.append((score, sym))
    scores.sort(reverse=True)
    return [sym for _, sym in scores[:top_n]]
