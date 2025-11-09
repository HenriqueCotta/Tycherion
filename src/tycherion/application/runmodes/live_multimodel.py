from __future__ import annotations
import time
from datetime import datetime, timedelta, timezone
from tycherion.shared.config import AppConfig
from tycherion.ports.market_data import MarketDataPort
from tycherion.ports.trading import TradingPort
from tycherion.ports.account import AccountPort
from tycherion.ports.universe import UniversePort
from tycherion.application.plugins.registry import MODELS, ALLOCATORS, BALANCERS, pick_indicator_for
from tycherion.application.services.coverage_selector import build_coverage
from tycherion.application.services.ensemble import combine
import MetaTrader5 as mt5

def run_live_multimodel(cfg: AppConfig, data: MarketDataPort, trader: TradingPort, account: AccountPort, universe: UniversePort) -> None:
    playbook = cfg.application.playbook or "default"
    active_models = [m for m in MODELS.values() if playbook in getattr(m, "tags", set()) or "default" in getattr(m, "tags", set())]
    if not active_models:
        print(f"No models found for playbook={playbook}. Nothing to do.")
        return
    needed_keys = set().union(*[m.requires() for m in active_models]) if active_models else set()

    coverage = build_coverage(cfg, data, universe)
    allocator = ALLOCATORS.get(cfg.application.portfolio.allocator)
    balancer = BALANCERS.get(cfg.application.portfolio.balancer)
    if allocator is None or balancer is None:
        raise SystemExit("Missing allocator/balancer plugin.")

    def step_once():
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=cfg.lookback_days)

        signed_signals = {}
        for symbol in coverage:
            if not mt5.symbol_select(symbol, True):
                print(f"[{symbol}] not available/visible.")
                continue
            df = data.get_bars(symbol, cfg.timeframe, start, end)
            if df.empty or len(df) < 30:
                print(f"[{symbol}] no data.")
                continue
            bundle = {}
            for key in needed_keys:
                ind = pick_indicator_for(key, playbook)
                try:
                    bundle[key] = ind.compute(df.copy())
                except Exception as e:
                    print(f"[{symbol}] indicator {key}:{getattr(ind,'method','?')} failed: {e}")
                    bundle[key] = {"score":0.0,"features":{}}
            decisions = []
            for model in active_models:
                try:
                    decisions.append(model.decide(bundle))
                except Exception as e:
                    print(f"[{symbol}] model {model.name} failed: {e}")
            final = combine(decisions)
            signed_signals[symbol] = float(final.get("signed", 0.0))

        target_weights = allocator.allocate(signed_signals)

        orders = balancer.plan(
            account=account,
            target=target_weights,
            volume_mode=cfg.trading.volume_mode,
            fixed_volume=cfg.trading.fixed_volume,
            threshold=cfg.application.portfolio.threshold_weight,
        )

        for od in orders:
            side = od.side.upper()
            if side == "BUY":
                trader.market_buy(od.symbol, volume=od.volume)
            elif side == "SELL":
                trader.market_sell(od.symbol, volume=od.volume)

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
