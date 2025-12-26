from __future__ import annotations

from tycherion.domain.signals.indicators.base import BaseIndicator
import pandas as pd

from tycherion.application.plugins.registry import register_indicator
from tycherion.domain.signals.entities import IndicatorOutput


@register_indicator(key="volatility", method="atr_14", tags={"default"})
class VolATR14(BaseIndicator):
    period = 14

    def compute(self, df: pd.DataFrame) -> IndicatorOutput:
        if df.empty or len(df) < self.period + 1:
            return IndicatorOutput(score=0.0, features={})
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        close = df["close"].astype(float)
        prev_close = close.shift(1)
        tr = (high - low).abs()
        tr = pd.concat(
            [tr, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)
        atr = tr.rolling(self.period).mean()
        val = float(atr.iloc[-1])
        score = 1.0 / (1.0 + val) if val > 0 else 0.0
        return IndicatorOutput(score=score, features={"atr": val})
