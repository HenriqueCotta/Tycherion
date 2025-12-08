from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class IndicatorOutput:
    """Standard output of an indicator for a single symbol.

    - score: aggregated metric in [-1, 1] (by convention in this project)
    - features: extra numeric features that models may consume.
    """

    score: float
    features: Dict[str, float]


@dataclass
class ModelDecision:
    """Per-model decision for a single symbol.

    side: "BUY" | "SELL" | "HOLD"
    weight: relative intensity (usually in [0, 1])
    confidence: confidence level in [0, 1]
    """

    side: str
    weight: float
    confidence: float

@dataclass
class AggregatedDecision:
    """
    Decisão agregada (ensemble) de todos os models para um símbolo.

    side       -> direção final ("BUY"/"SELL"/"HOLD")
    weight     -> intensidade em [0, 1]
    confidence -> confiança em [0, 1]
    signed     -> direção * intensidade em [-1, 1]
    """
    side: str
    weight: float
    confidence: float
    signed: float