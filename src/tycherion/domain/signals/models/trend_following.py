from __future__ import annotations

from typing import Dict

from tycherion.application.plugins.registry import register_model
from tycherion.domain.signals.entities import IndicatorOutput, ModelDecision


@register_model(name="trend_following", tags={"default"})
class TrendFollowing:
    def requires(self) -> set[str]:
        return {"trend", "volatility"}

    def decide(self, indicators: Dict[str, IndicatorOutput]) -> ModelDecision:
        trend = indicators.get("trend") if indicators is not None else None
        tr = float(trend.score) if trend else 0.0

        if tr > 0.2:
            return ModelDecision(
                side="BUY",
                weight=min(1.0, 0.5 + tr * 0.5),
                confidence=0.7,
            )
        if tr < -0.2:
            return ModelDecision(
                side="SELL",
                weight=min(1.0, 0.5 + (-tr) * 0.5),
                confidence=0.7,
            )
        return ModelDecision(side="HOLD", weight=0.0, confidence=0.3)
