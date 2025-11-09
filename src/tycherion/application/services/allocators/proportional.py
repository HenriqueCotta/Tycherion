from __future__ import annotations
from typing import Dict
from tycherion.application.plugins.registry import register_allocator

@register_allocator(name="proportional", tags={"default"})
class ProportionalAllocator:
    def allocate(self, signals: Dict[str, float]) -> Dict[str, float]:
        abs_sum = sum(abs(v) for v in signals.values())
        if abs_sum <= 0:
            return {s: 0.0 for s in signals}
        return {s: (v/abs_sum) for s, v in signals.items()}
