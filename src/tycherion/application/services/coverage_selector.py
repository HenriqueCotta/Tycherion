from __future__ import annotations

from tycherion.shared.config import AppConfig
from tycherion.ports.market_data import MarketDataPort
from tycherion.ports.universe import UniversePort


def _build_base_coverage(cfg: AppConfig, universe: UniversePort) -> list[str]:
    """Build the *structural* universe of symbols.

    Coverage is intentionally dumb. It only answers: *which* symbols should be
    considered, based on the configured source. Any kind of "smart filtering"
    (liquidity, regimes, sanity checks, alpha, etc.) must live in the model
    pipeline, not here.
    """
    src = (cfg.application.coverage.source or "").lower()
    if src == "static":
        # Remove duplicates while preserving order
        return list(dict.fromkeys(cfg.application.coverage.symbols or []))
    if src == "market_watch":
        return universe.visible_symbols()
    if src == "pattern":
        patt = cfg.application.coverage.pattern or "*"
        return universe.by_pattern(patt)
    return universe.visible_symbols()


def build_coverage(cfg: AppConfig, data: MarketDataPort, universe: UniversePort) -> list[str]:
    """Build the list of symbols to analyse in this run.

    NOTE: `data` is kept in the signature for backward compatibility, but is
    intentionally unused. The universe thinning that previously depended on
    recent `tick_volume` (coverage.top_n) is deprecated and removed.
    """
    _ = data  # explicit unused
    return _build_base_coverage(cfg, universe)
