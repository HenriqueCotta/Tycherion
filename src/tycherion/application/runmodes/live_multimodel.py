from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from tycherion.shared.config import AppConfig, PipelineStageCfg
from tycherion.ports.market_data import MarketDataPort
from tycherion.ports.trading import TradingPort
from tycherion.ports.account import AccountPort
from tycherion.ports.universe import UniversePort
from tycherion.application.plugins.registry import (
    MODELS,
    ALLOCATORS,
    BALANCERS,
    pick_indicator_for,
)
from tycherion.application.services.coverage_selector import build_coverage
from tycherion.application.services.ensemble import combine
from tycherion.application.services.order_planner import build_orders
from tycherion.domain.portfolio.entities import (
    Signal,
    SignalsBySymbol,
    PortfolioSnapshot,
    Position,
)
from tycherion.domain.signals.entities import (
    IndicatorOutput,
    ModelDecision,
    SymbolState,
    ModelStageResult,
)


def _build_portfolio_snapshot(account: AccountPort) -> PortfolioSnapshot:
    equity = float(account.equity())
    positions: Dict[str, Position] = {}
    for p in account.positions():
        positions[p.symbol] = p
    return PortfolioSnapshot(equity=equity, positions=positions)


def _decision_to_score(d: ModelDecision) -> float:
    """Map a ModelDecision into a numeric score in [-1, 1]."""
    side = (d.side or "HOLD").upper()
    w = float(d.weight or 0.0)
    w = max(0.0, min(1.0, w))
    if side == "BUY":
        s = w
    elif side == "SELL":
        s = -w
    else:
        s = 0.0
    return max(-1.0, min(1.0, s))


def _resolve_pipeline(cfg: AppConfig) -> List[Tuple[PipelineStageCfg, object]]:
    stages = list(cfg.application.models.pipeline or [])
    if not stages:
        raise RuntimeError(
            "No model pipeline configured. Please set application.models.pipeline in your YAML."
        )

    pipeline: List[Tuple[PipelineStageCfg, object]] = []
    for stage in stages:
        name = stage.name
        model = MODELS.get(name)
        if not model:
            available = ", ".join(sorted(MODELS.keys()))
            raise RuntimeError(f"Model not found: {name!r}. Available models: {available}")
        pipeline.append((stage, model))
    return pipeline


def run_live_multimodel(
    cfg: AppConfig,
    data: MarketDataPort,
    trader: TradingPort,
    account: AccountPort,
    universe: UniversePort,
) -> None:
    """Live runmode executing an ordered model pipeline per symbol."""
    playbook = cfg.application.playbook or "default"

    allocator = ALLOCATORS.get(cfg.application.portfolio.allocator)
    if not allocator:
        raise RuntimeError(f"Allocator not found: {cfg.application.portfolio.allocator!r}")

    balancer = BALANCERS.get(cfg.application.portfolio.balancer)
    if not balancer:
        raise RuntimeError(f"Balancer not found: {cfg.application.portfolio.balancer!r}")

    pipeline = _resolve_pipeline(cfg)
    print(f"[models] pipeline={[stage.name for stage, _ in pipeline]}")
    print(f"[plugins] available_models={len(MODELS)}")

    def step_once() -> None:
        # 1) Structural symbol universe from coverage + ensure held symbols are included
        coverage = build_coverage(cfg, data, universe)
        current_positions = account.positions()
        held_symbols = {p.symbol for p in current_positions}
        coverage = sorted(set(coverage) | held_symbols)
        print(f"[coverage] {len(coverage)} symbols -> {coverage}")

        # 2) Initialise per-symbol state
        states: Dict[str, SymbolState] = {
            sym: SymbolState(symbol=sym, is_held=(sym in held_symbols))
            for sym in coverage
        }

        # 3) Portfolio snapshot (before new trades)
        portfolio = _build_portfolio_snapshot(account)

        # 4) Time window for analysis
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=cfg.lookback_days)

        # 5) Determine which indicators we need for the whole pipeline
        needed_keys: set[str] = set()
        for _, model in pipeline:
            try:
                needed_keys.update(model.requires() or set())
            except Exception:
                pass
        print(f"[indicators] needed_keys={sorted(needed_keys)}")

        # 6) Per-symbol model pipeline
        for symbol, state in states.items():
            if not state.alive and not state.is_held:
                continue

            try:
                df = data.get_bars(symbol, cfg.timeframe, start, end)
            except Exception as e:
                print(f"[{symbol}] data error: {e}")
                state.notes["data_error"] = 1.0
                if not state.is_held:
                    state.alive = False
                continue

            if df is None or df.empty:
                print(f"[{symbol}] no data.")
                state.notes["no_data"] = 1.0
                if not state.is_held:
                    state.alive = False
                continue

            # Compute indicators once and share across models
            bundle: Dict[str, IndicatorOutput] = {}
            for key in needed_keys:
                ind = pick_indicator_for(key, playbook)
                try:
                    bundle[key] = ind.compute(df.copy())
                except Exception as e:
                    print(f"[{symbol}] indicator {key}:{getattr(ind, 'method', '?')} failed: {e}")
                    bundle[key] = IndicatorOutput(score=0.0, features={})

            stage_decisions: list[ModelDecision] = []

            for stage_cfg, model in pipeline:
                if not state.alive and not state.is_held:
                    break

                stage_name = stage_cfg.name
                try:
                    decision: ModelDecision = model.decide(bundle)
                except Exception as e:
                    print(f"[{symbol}] model {stage_name} failed: {e}")
                    decision = ModelDecision(side="HOLD", weight=0.0, confidence=0.0)
                    state.notes[f"model_error_{stage_name}"] = 1.0

                stage_decisions.append(decision)

                score = _decision_to_score(decision)
                state.pipeline_results.append(
                    ModelStageResult(model_name=stage_name, score=score)
                )

                threshold = (
                    float(stage_cfg.drop_threshold)
                    if stage_cfg.drop_threshold is not None
                    else float(getattr(model, "drop_threshold", -1.0))
                )

                if score < threshold:
                    if state.is_held:
                        # Held symbols are never silently discarded. Keep going, but record the fact.
                        state.notes[f"below_threshold_{stage_name}"] = 1.0
                    else:
                        state.alive = False
                        state.notes[f"dropped_by_{stage_name}"] = 1.0
                        break

            agg = combine(stage_decisions)
            state.alpha_score = float(agg.signed)
            state.notes["final_confidence"] = float(agg.confidence)
            state.notes["final_side"] = 1.0 if agg.side == "BUY" else (-1.0 if agg.side == "SELL" else 0.0)

        # 7) Convert states into SignalsBySymbol for the allocator
        signals: SignalsBySymbol = {}
        for symbol, state in states.items():
            if not state.alive and not state.is_held:
                continue
            signed = float(state.alpha_score)
            confidence = float(state.notes.get("final_confidence", 1.0))
            signals[symbol] = Signal(symbol=symbol, signed=signed, confidence=confidence)

        # 8) Allocation -> target weights
        target_alloc = allocator.allocate(signals)

        # 9) Balancing -> rebalance plan
        plan = balancer.plan(
            portfolio=portfolio,
            target=target_alloc,
            threshold=cfg.application.portfolio.threshold_weight,
        )
        print(f"[rebalance] plan={len(plan)} instructions")

        # 10) Orders -> execution
        orders = build_orders(portfolio, plan, cfg.trading)
        print(f"[orders] {len(orders)} orders to execute")

        for od in orders:
            if od.side.upper() == "BUY":
                res = trader.market_buy(od.symbol, volume=od.volume)
            else:
                res = trader.market_sell(od.symbol, volume=od.volume)
            print(f"[trade] {od.side} {od.symbol} vol={od.volume} -> {res}")

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
