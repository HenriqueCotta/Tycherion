from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Dict

from tycherion.shared.config import AppConfig
from tycherion.ports.market_data import MarketDataPort
from tycherion.ports.trading import TradingPort
from tycherion.ports.account import AccountPort, Position
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
from tycherion.domain.portfolio.types import (
    Signal,
    SignalsBySymbol,
    PortfolioSnapshot,
    PortfolioPosition,
)


def _build_portfolio_snapshot(account: AccountPort) -> PortfolioSnapshot:
    equity = float(account.equity())
    positions: Dict[str, PortfolioPosition] = {}
    for p in account.positions():
        # ports.account.Position has (symbol, volume, price)
        positions[p.symbol] = PortfolioPosition(
            symbol=p.symbol,
            quantity=float(p.volume),
            price=float(p.price),
        )
    return PortfolioSnapshot(equity=equity, positions=positions)


def run_live_multimodel(
    cfg: AppConfig,
    data: MarketDataPort,
    trader: TradingPort,
    account: AccountPort,
    universe: UniversePort,
) -> None:
    """
    Main live runmode:
    - build coverage of symbols to analyse
    - compute indicators and model decisions per symbol
    - aggregate into a signal per symbol
    - allocate target portfolio weights
    - compute rebalance instructions
    - translate into concrete orders and send to the broker
    """
    playbook = cfg.application.playbook or "default"

    # Select active models for the current playbook
    active_models = [
        m
        for m in MODELS.values()
        if playbook in getattr(m, "tags", set())
        or "default" in getattr(m, "tags", set())
        or not getattr(m, "tags", set())
    ]

    if not active_models:
        raise RuntimeError("No models registered for the current playbook.")

    allocator = ALLOCATORS.get(cfg.application.portfolio.allocator)
    if not allocator:
        raise RuntimeError(f"Allocator not found: {cfg.application.portfolio.allocator!r}")

    balancer = BALANCERS.get(cfg.application.portfolio.balancer)
    if not balancer:
        raise RuntimeError(f"Balancer not found: {cfg.application.portfolio.balancer!r}")

    def step_once() -> None:
        # Build symbol universe
        coverage = build_coverage(cfg, data, universe)

        # Ensure we never ignore current positions
        current_positions = account.positions()
        held_symbols = {p.symbol for p in current_positions}
        coverage = sorted(set(coverage) | held_symbols)

        print(f"[coverage] {len(coverage)} symbols -> {coverage}")

        # Build portfolio snapshot (before new trades)
        portfolio = _build_portfolio_snapshot(account)

        # Time window for analysis
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=cfg.lookback_days)

        # Determine which indicators we need for all active models
        needed_keys = set()
        for m in active_models:
            try:
                req = m.requires()
            except Exception:
                req = set()
            needed_keys.update(req or [])
        print(f"[models] active={len(active_models)} needed_indicators={needed_keys}")

        signals: SignalsBySymbol = {}

        for symbol in coverage:
            try:
                df = data.get_bars(symbol, cfg.timeframe, start, end)
            except Exception as e:
                print(f"[{symbol}] failed to load data: {e}")
                continue

            if df is None or df.empty:
                print(f"[{symbol}] no data.")
                continue

            # Build indicator bundle (key -> result dict)
            bundle: Dict[str, dict] = {}
            for key in needed_keys:
                ind = pick_indicator_for(key, playbook)
                try:
                    bundle[key] = ind.compute(df.copy())
                except Exception as e:
                    print(
                        f"[{symbol}] indicator {key}:{getattr(ind, 'method', '?')} "
                        f"failed: {e}"
                    )
                    bundle[key] = {"score": 0.0, "features": {}}

            decisions = []
            for model in active_models:
                try:
                    decisions.append(model.decide(bundle))
                except Exception as e:
                    print(f"[{symbol}] model {getattr(model, 'name', '?')} failed: {e}")

            final = combine(decisions)
            signed = float(final.get("signed", 0.0))
            conf = float(final.get("confidence", 0.0))
            signals[symbol] = Signal(symbol=symbol, signed=signed, confidence=conf)

        # 1) Allocation: signals + portfolio -> target allocation (weights)
        target_alloc = allocator.allocate(signals)  # TargetAllocation

        # 2) Balancing: current portfolio + target allocation -> rebalance plan
        plan = balancer.plan(
            portfolio=portfolio,
            target=target_alloc,
            threshold=cfg.application.portfolio.threshold_weight,
        )

        print(f"[rebalance] plan={len(plan)} instructions")

        # 3) Order sizing: rebalance plan -> concrete orders with volumes
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
