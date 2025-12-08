from __future__ import annotations

from dataclasses import dataclass
from typing import List

from tycherion.domain.portfolio.types import PortfolioSnapshot, RebalanceInstruction
from tycherion.shared.config import Trading


@dataclass
class SuggestedOrder:
    symbol: str
    side: str   # "BUY" | "SELL"
    volume: float


def build_orders(
    portfolio: PortfolioSnapshot,
    plan: List[RebalanceInstruction],
    trading_cfg: Trading,
) -> List[SuggestedOrder]:
    """
    Convert domain-level rebalance instructions (expressed in weights) into
    concrete order suggestions with broker volumes. This is the point where
    we cross from the pure portfolio domain into broker-specific constraints.
    """
    # Lazy import to avoid circular deps
    from tycherion.application.services.sizer import (
        volume_from_weight,
        symbol_min_volume,
    )

    orders: List[SuggestedOrder] = []
    for instr in plan:
        # For now we scale volumes solely by absolute delta_weight. In the
        # future this can incorporate volatility, risk, etc.
        w = abs(float(instr.delta_weight))
        if w <= 0.0:
            continue

        vol = volume_from_weight(
            instr.symbol,
            w,
            trading_cfg.volume_mode,
            trading_cfg.fixed_volume,
        )
        min_vol = symbol_min_volume(instr.symbol)
        vol = max(vol, min_vol)
        if vol <= 0.0:
            continue

        orders.append(
            SuggestedOrder(
                symbol=instr.symbol,
                side=instr.side,
                volume=vol,
            )
        )
    return orders
