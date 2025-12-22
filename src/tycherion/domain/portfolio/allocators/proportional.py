from __future__ import annotations

from tycherion.application.plugins.registry import register_allocator
from tycherion.domain.portfolio.entities import SignalsBySymbol, TargetAllocation


@register_allocator(name="proportional", tags={"default"})
class ProportionalAllocator:
    """
    Allocator that gives each symbol a weight proportional to the absolute
    value of its signal. Signals are normalised so that the sum of absolute
    weights is 1. Longs get +w, shorts get -w.
    """
    def allocate(self, signals: SignalsBySymbol) -> TargetAllocation:
        total = sum(abs(float(s.signed)) for s in signals.values())
        if total <= 1e-9:
            return TargetAllocation(weights={})

        weights: dict[str, float] = {}
        for sig in signals.values():
            if sig.signed == 0:
                weights[sig.symbol] = 0.0
            else:
                frac = abs(float(sig.signed)) / total
                weights[sig.symbol] = frac if sig.signed > 0 else -frac
        return TargetAllocation(weights=weights)
