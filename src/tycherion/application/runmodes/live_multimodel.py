from __future__ import annotations
import time
from datetime import datetime, timedelta, timezone

from tycherion.shared.config import AppConfig
from tycherion.ports.market_data import MarketDataPort
from tycherion.ports.trading import TradingPort
from tycherion.ports.account import AccountPort
from tycherion.ports.universe import UniversePort

from tycherion.application.plugins.registry import MODELS, pick_indicator_for
from tycherion.application.services.coverage_selector import build_coverage
from tycherion.application.services.ensemble import combine
from tycherion.application.services.sizer import volume_from_weight

import MetaTrader5 as mt5
import pandas as pd

def run_live_multimodel(cfg: AppConfig, data: MarketDataPort, trader: TradingPort, account: AccountPort, universe: UniversePort) -> None:
    playbook = cfg.application.playbook or "default"
    activeModels = [model for model in MODELS.values() if playbook in getattr(model, "tags", set()) or "default" in getattr(model, "tags", set())]
    if not activeModels:
        print(f"No models found for playbook={playbook}. Nothing to do.")
        return
    needed_keys = set().union(*[m.requires() for m in activeModels]) if activeModels else set()
    coverage = build_coverage(cfg, data, universe)

    def step_once():
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=cfg.lookback_days)
        for symbol in coverage:
            if not mt5.symbol_select(symbol, True):
                print(f"[{symbol}] not available/visible.")
                continue
            dataFrame = data.get_bars(symbol, cfg.timeframe, start, end)
            if dataFrame.empty or len(dataFrame) < 30:
                print(f"[{symbol}] no data.")
                continue
            bundle = {}
            for key in needed_keys:
                ind = pick_indicator_for(key, playbook)
                try:
                    bundle[key] = ind.compute(dataFrame.copy())
                except Exception as e:
                    print(f"[{symbol}] indicator {key}:{getattr(ind,'method','?')} failed: {e}")
                    bundle[key] = {"score":0.0,"features":{}}
            decisions = []
            for model in activeModels:
                try:
                    decisionByModel = model.decide(bundle)
                    decisions.append(decisionByModel)
                except Exception as e:
                    print(f"[{symbol}] model {model.name} failed: {e}")
            final = combine(decisions)
            side = final["side"]; weight = final["weight"]
            vol = volume_from_weight(symbol, weight, cfg.trading.volume_mode, cfg.trading.fixed_volume)
            if vol <= 0.0 or side == "HOLD":
                print(f"[{symbol}] ENSEMBLE -> HOLD (weight={weight:.2f})")
                continue
            print(f"[{symbol}] ENSEMBLE -> {side} (weight={weight:.2f}) vol≈{vol}")
            if side == "BUY":
                trader.market_buy(symbol)
            elif side == "SELL":
                trader.market_sell(symbol)

    if cfg.application.schedule.run_forever:
        while True:
            try:
                step_once()
                time.sleep(max(1, cfg.application.schedule.interval_seconds))
            except KeyboardInterrupt:
                print("Stopping by keyboard.")
                break
            except Exception as e:
                print("Loop error:", e)
                time.sleep(3)
    else:
        step_once()
