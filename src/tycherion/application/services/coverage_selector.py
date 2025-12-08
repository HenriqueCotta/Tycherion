from __future__ import annotations
from datetime import datetime, timedelta, timezone
import pandas as pd
from tycherion.shared.config import AppConfig
from tycherion.ports.market_data import MarketDataPort
from tycherion.ports.universe import UniversePort

def build_coverage(cfg: AppConfig, data: MarketDataPort, universe: UniversePort) -> list[str]:
    src = cfg.application.coverage.source
    if src == "static":
        base = list(dict.fromkeys(cfg.application.coverage.symbols or []))
    elif src == "market_watch":
        base = universe.visible_symbols()
    elif src == "pattern":
        patt = cfg.application.coverage.pattern or "*"
        base = universe.by_pattern(patt)
    else:
        base = universe.visible_symbols()

    top_n = cfg.application.coverage.top_n or 0
    if top_n <= 0 or len(base) <= top_n:
        return base

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(cfg.lookback_days, 15))
    scores: list[tuple[float, str]] = []
    for sym in base[:300]:
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

