from __future__ import annotations
from tycherion.application.plugins.registry import register_model

@register_model(name="trend_following", tags={"default"})
class TrendFollowing:
    def requires(self): 
        return {"trend","volatility"}
    def decide(self, indicators):
        tr = float(indicators.get("trend",{}).get("score",0.0))
        if tr > 0.2:
            return {"side":"BUY","weight": min(1.0, 0.5 + tr*0.5),"confidence":0.7}
        if tr < -0.2:
            return {"side":"SELL","weight": min(1.0, 0.5 + (-tr)*0.5),"confidence":0.7}
        return {"side":"HOLD","weight":0.0,"confidence":0.3}
