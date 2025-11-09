from __future__ import annotations
from typing import Dict
from tycherion.application.plugins.registry import register_allocator

@register_allocator(name="equal_weight", tags={"default"})
class EqualWeightAllocator:
    def allocate(self, signals: Dict[str, float]) -> Dict[str, float]:
        nonzero = [s for s,v in signals.items() if abs(v) > 1e-6]
        if not nonzero:
            return {s: 0.0 for s in signals}
        w = 1.0 / len(nonzero)
        out = {}
        for s, v in signals.items():
            out[s] = (w if v > 0 else (-w if v < 0 else 0.0))
        return out
