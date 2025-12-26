from __future__ import annotations

from tycherion.domain.signals.indicators.base import BaseIndicator
import pandas as pd

from tycherion.application.plugins.registry import register_indicator
from tycherion.domain.signals.entities import IndicatorOutput


@register_indicator(key="trend", method="donchian_50_50", tags={"default"})
class TrendDonchian5050(BaseIndicator):
    high_n = 50
    low_n = 50

    def compute(self, df: pd.DataFrame) -> IndicatorOutput:
        if df.empty or len(df) < max(self.high_n, self.low_n):
            return IndicatorOutput(score=0.0, features={})
        hh = df["high"].rolling(self.high_n).max()
        ll = df["low"].rolling(self.low_n).min()
        mid = (hh + ll) / 2.0
        rng = (hh - ll).replace(0, 1e-9)
        pos = (df["close"] - mid) / (rng / 2.0)
        score = float(pos.iloc[-1])
        score = max(-1.0, min(1.0, score))
        return IndicatorOutput(
            score=score,
            features={"upper": float(hh.iloc[-1]), "lower": float(ll.iloc[-1])},
        )
