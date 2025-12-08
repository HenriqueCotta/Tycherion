from __future__ import annotations
from tycherion.application.plugins.registry import register_model

@register_model(name="mean_reversion", tags={"default"})
class MeanReversion:
    def requires(self):
        return {"stretch","volatility"}
    def decide(self, indicators):
        z = float(indicators.get("stretch",{}).get("features",{}).get("z", 0.0))
        if z <= -2.0:
            w = min(1.0, abs(z)/3.0)
            return {"side":"BUY","weight": w, "confidence":0.6}
        if z >= 2.0:
            w = min(1.0, abs(z)/3.0)
            return {"side":"SELL","weight": w, "confidence":0.6}
        return {"side":"HOLD","weight":0.0,"confidence":0.4}
