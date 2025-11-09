from __future__ import annotations
from typing import List, Dict

def combine(decisions: List[Dict]) -> Dict:
    if not decisions:
        return {'side':'HOLD','weight':0.0,'confidence':0.0, 'signed': 0.0}
    num, den = 0.0, 0.0
    for d in decisions:
        side = d.get('side','HOLD')
        w = float(d.get('weight',0.0))
        c = float(d.get('confidence',0.5))
        signed = w if side == 'BUY' else (-w if side == 'SELL' else 0.0)
        num += signed * max(0.0, min(1.0, c))
        den += max(0.0, min(1.0, c))
    if den <= 0:
        return {'side':'HOLD','weight':0.0,'confidence':0.0, 'signed': 0.0}
    s = num / den
    side = 'BUY' if s > 0.1 else ('SELL' if s < -0.1 else 'HOLD')
    weight = min(1.0, abs(s))
    return {'side': side, 'weight': weight, 'confidence': min(1.0, den/len(decisions)), 'signed': s}
