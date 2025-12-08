from __future__ import annotations

from tycherion.application.plugins.registry import register_balancer
from tycherion.domain.portfolio.entities import (
    PortfolioSnapshot,
    TargetAllocation,
    RebalanceInstruction,
)


@register_balancer(name="threshold", tags={"default"})
class ThresholdBalancer:
    """
    Domain-level balancer: generates rebalance instructions whenever the
    difference between current and target weight is greater than or equal
    to a configured threshold.
    """
    def plan(
        self,
        portfolio: PortfolioSnapshot,
        target: TargetAllocation,
        threshold: float = 0.25,
    ) -> list[RebalanceInstruction]:
        threshold = max(0.0, min(1.0, float(threshold)))
        instructions: list[RebalanceInstruction] = []

        symbols = set(target.weights.keys()) | set(portfolio.positions.keys())
        for sym in sorted(symbols):
            current_w = float(portfolio.weight_of(sym))
            target_w = float(target.weights.get(sym, 0.0))
            delta = target_w - current_w
            if abs(delta) < threshold:
                continue
            side = "BUY" if delta > 0 else "SELL"
            instructions.append(
                RebalanceInstruction(
                    symbol=sym,
                    from_weight=current_w,
                    to_weight=target_w,
                    delta_weight=delta,
                    side=side,
                )
            )
        return instructions

