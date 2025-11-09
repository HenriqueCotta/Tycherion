from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
from tycherion.application.plugins.registry import register_balancer
from tycherion.ports.account import AccountPort
from tycherion.application.services.sizer import volume_from_weight, symbol_min_volume

@dataclass
class SuggestedOrder:
    symbol: str
    side: str   # 'BUY' | 'SELL'
    volume: float

@register_balancer(name="threshold", tags={"default"})
class ThresholdBalancer:
    def plan(self, account: AccountPort, target: Dict[str, float], *, volume_mode: str, fixed_volume: float, threshold: float = 0.25) -> List[SuggestedOrder]:
        out: List[SuggestedOrder] = []
        for sym, tw in target.items():
            if abs(tw) < max(0.0, min(1.0, threshold)):
                continue
            side = "BUY" if tw > 0 else "SELL"
            vol = volume_from_weight(sym, abs(tw), volume_mode, fixed_volume)
            vol = max(vol, symbol_min_volume(sym))
            out.append(SuggestedOrder(symbol=sym, side=side, volume=vol))
        return out
