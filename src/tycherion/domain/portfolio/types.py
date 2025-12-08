from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


Symbol = str


@dataclass
class Signal:
    """
    Per-symbol signal produced by the models/ensemble.
    signed: desired direction/intensity in [-1, 1]
    confidence: optional confidence level in [0, 1]
    """
    symbol: Symbol
    signed: float
    confidence: float = 1.0


SignalsBySymbol = Dict[Symbol, Signal]


@dataclass
class PortfolioPosition:
    """
    Snapshot of a single position in the portfolio, in abstract units
    (shares, contracts, etc.). Price is the best estimate available
    (e.g. last close, or average price).
    """
    symbol: Symbol
    quantity: float
    price: float


@dataclass
class PortfolioSnapshot:
    """
    Portfolio snapshot used by allocators/balancers at the domain level.
    Equity is the current account equity in account currency.
    """
    equity: float
    positions: Dict[Symbol, PortfolioPosition]

    def weight_of(self, symbol: Symbol) -> float:
        pos = self.positions.get(symbol)
        if not pos or self.equity <= 0:
            return 0.0
        return float(pos.quantity * pos.price) / float(self.equity)


@dataclass
class TargetAllocation:
    """
    Target portfolio allocation expressed as weights per symbol in [-1, 1].
    Positive weights are long exposure, negative weights are short exposure.
    """
    weights: Dict[Symbol, float]


@dataclass
class RebalanceInstruction:
    """
    Domain-level rebalance instruction expressed in weights, not broker
    volumes. Conversion to concrete order sizes happens in the application
    layer (order planner).
    """
    symbol: Symbol
    from_weight: float
    to_weight: float
    delta_weight: float
    side: str  # "BUY" | "SELL"
