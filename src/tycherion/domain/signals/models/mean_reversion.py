from __future__ import annotations

from tycherion.domain.signals.models.base import SignalModel
from typing import Dict

from tycherion.application.plugins.registry import register_model
from tycherion.domain.signals.entities import IndicatorOutput, ModelDecision


@register_model(name="mean_reversion", tags={"default"})
class MeanReversion(SignalModel):
    def requires(self) -> set[str]:
        return {"stretch", "volatility"}

    def decide(self, indicators: Dict[str, IndicatorOutput]) -> ModelDecision:
        stretch = indicators.get("stretch") if indicators is not None else None
        z = float(stretch.features.get("z", 0.0)) if stretch else 0.0

        if z <= -2.0:
            w = min(1.0, abs(z) / 3.0)
            return ModelDecision(side="BUY", weight=w, confidence=0.6)
        if z >= 2.0:
            w = min(1.0, abs(z) / 3.0)
            return ModelDecision(side="SELL", weight=w, confidence=0.6)
        return ModelDecision(side="HOLD", weight=0.0, confidence=0.4)

