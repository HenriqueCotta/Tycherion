from __future__ import annotations

from tycherion.application.plugins.registry import register_allocator
from tycherion.domain.portfolio.entities import SignalsBySymbol, TargetAllocation


@register_allocator(name="equal_weight", tags={"default"})
class EqualWeightAllocator:
    """
    Simple allocator: gives the same absolute weight to all symbols that have
    a non-zero signal. Longs get +w, shorts get -w, holds get 0.
    """
    def allocate(self, signals: SignalsBySymbol) -> TargetAllocation:
        nonzero = [s for s in signals.values() if abs(float(s.signed)) > 1e-6]
        if not nonzero:
            # nothing to do
            return TargetAllocation(weights={})

        w = 1.0 / float(len(nonzero))
        weights: dict[str, float] = {}
        for sig in signals.values():
            if sig.signed > 0:
                weights[sig.symbol] = w
            elif sig.signed < 0:
                weights[sig.symbol] = -w
            else:
                weights[sig.symbol] = 0.0
        return TargetAllocation(weights=weights)

