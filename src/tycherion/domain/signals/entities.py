from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


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


@dataclass
class ModelStageResult:
    """Result for a symbol at a specific model stage in the pipeline."""

    model_name: str
    score: float


@dataclass
class SymbolState:
    """Mutable per-symbol state that flows through the analysis pipeline.

    This is intentionally generic so we can reuse it for universe filters,
    macro models and per-symbol alpha models over time.
    """
    symbol: str
    is_held: bool = False      # True if the symbol is currently in the portfolio
    alive: bool = True         # If False and not held, the symbol can be dropped from the pipeline

    base_score: float = 0.0    # Optional starting score (e.g. from simple filters)
    sanity_score: float = 0.0  # Data-quality / tradability / liquidity score
    macro_score: float = 0.0   # Macro / regime score for this symbol
    alpha_score: float = 0.0   # Final alpha-like score, typically coming from signal models

    pipeline_results: List[ModelStageResult] = field(default_factory=list)

    notes: Dict[str, float] = field(default_factory=dict)

