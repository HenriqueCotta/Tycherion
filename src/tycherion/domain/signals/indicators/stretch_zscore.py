from __future__ import annotations

import pandas as pd

from tycherion.application.plugins.registry import register_indicator
from tycherion.domain.signals.entities import IndicatorOutput


@register_indicator(key="stretch", method="zscore_20", tags={"default"})
class StretchZScore20:
    period = 20

    def compute(self, df: pd.DataFrame) -> IndicatorOutput:
        if df.empty or len(df) < self.period:
            return IndicatorOutput(score=0.0, features={})
        close = df["close"].astype(float)
        ma = close.rolling(self.period).mean()
        sd = close.rolling(self.period).std(ddof=0).replace(0, 1e-9)
        z = (close - ma) / sd
        zval = float(z.iloc[-1])
        score = max(-1.0, min(1.0, -zval / 3.0))
        return IndicatorOutput(score=score, features={"z": zval})
