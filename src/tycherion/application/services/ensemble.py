from __future__ import annotations
from typing import List, Dict

def combine(decisions: List[Dict]) -> Dict:
    # Confidence-weighted average of signed weights.
    # Each decision: {'side':'BUY|SELL|HOLD','weight':0..1,'confidence':0..1}
    if not decisions:
        return {'side':'HOLD','weight':0.0,'confidence':0.0}

    num, den = 0.0, 0.0
    for decision in decisions:
        side = decision.get('side','HOLD')
        weight = float(decision.get('weight',0.0))
        confidence = float(decision.get('confidence',0.5))
        signed = weight if side == 'BUY' else (-weight if side == 'SELL' else 0.0)
        num += signed * max(0.0, min(1.0, confidence))
        den += max(0.0, min(1.0, confidence))

    if den <= 0.0:
        return {'side':'HOLD','weight':0.0,'confidence':0.0}
    agg = num / den
    side = 'BUY' if agg > 0.1 else ('SELL' if agg < -0.1 else 'HOLD')
    weight = min(1.0, abs(agg))
    return {'side': side, 'weight': weight, 'confidence': min(1.0, den/len(decisions))}
