from __future__ import annotations
import MetaTrader5 as mt5

def symbol_min_volume(symbol: str) -> float:
    info = mt5.symbol_info(symbol)
    if not info:
        return 0.0
    v = max(info.volume_min, info.volume_step)
    steps = round(v / info.volume_step)
    return steps * info.volume_step

def volume_from_weight(symbol: str, weight: float, mode: str, fixed_volume: float) -> float:
    """
    MVP sizing:
    
     - 'min': use min volume if weight > 0; else 0.
     
     - 'fixed': scale fixed_volume by weight.
    """
    weight = max(0.0, min(1.0, float(weight)))
    if weight < 1e-6:
        return 0.0
    if mode == 'fixed':
        return float(fixed_volume) * weight
    # default: min
    return symbol_min_volume(symbol)
