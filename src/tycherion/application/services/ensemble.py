# application/services/ensemble.py (versão nova)

from __future__ import annotations

from typing import List
from tycherion.domain.signals.entities import ModelDecision, AggregatedDecision


def combine(decisions: List[ModelDecision]) -> AggregatedDecision:
    """
    Combina uma lista de ModelDecision em uma decisão agregada única.
    """
    if not decisions:
        return AggregatedDecision(
            side="HOLD",
            weight=0.0,
            confidence=0.0,
            signed=0.0,
        )

    num, den = 0.0, 0.0
    for d in decisions:
        side = (d.side or "HOLD").upper()
        w = float(d.weight)
        c = float(d.confidence if d.confidence is not None else 0.5)
        c = max(0.0, min(1.0, c))

        if side == "BUY":
            signed = w
        elif side == "SELL":
            signed = -w
        else:
            signed = 0.0

        num += signed * c
        den += c

    if den <= 0:
        return AggregatedDecision(
            side="HOLD",
            weight=0.0,
            confidence=0.0,
            signed=0.0,
        )

    s = num / den
    side = "BUY" if s > 0.1 else ("SELL" if s < -0.1 else "HOLD")
    weight = min(1.0, abs(s))
    confidence = min(1.0, den / max(1, len(decisions)))

    return AggregatedDecision(
        side=side,
        weight=weight,
        confidence=confidence,
        signed=s,
    )

