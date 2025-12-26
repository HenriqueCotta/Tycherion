from __future__ import annotations

import time
from typing import Dict

from tycherion.shared.config import AppConfig
from tycherion.ports.trading import TradingPort
from tycherion.ports.account import AccountPort
from tycherion.ports.universe import UniversePort

from tycherion.application.plugins.registry import (
    ALLOCATORS,
    BALANCERS,
)
from tycherion.application.services.coverage_selector import build_coverage
from tycherion.application.services.order_planner import build_orders
from tycherion.domain.portfolio.entities import (
    PortfolioSnapshot,
    Position,
)

from tycherion.application.pipeline.config import build_pipeline_config
from tycherion.application.pipeline.service import ModelPipelineService


def _build_portfolio_snapshot(account: AccountPort) -> PortfolioSnapshot:
    equity = float(account.equity())
    positions: Dict[str, Position] = {}
    for p in account.positions():
        positions[p.symbol] = p
    return PortfolioSnapshot(equity=equity, positions=positions)


def run_live_multimodel(
    cfg: AppConfig,
    trader: TradingPort,
    account: AccountPort,
    universe: UniversePort,
    pipeline_service: ModelPipelineService,
) -> None:
    """Live runmode that delegates per-symbol pipeline execution to ModelPipelineService."""

    allocator = ALLOCATORS.get(cfg.application.portfolio.allocator)
    if not allocator:
        raise RuntimeError(f"Allocator not found: {cfg.application.portfolio.allocator!r}")

    balancer = BALANCERS.get(cfg.application.portfolio.balancer)
    if not balancer:
        raise RuntimeError(f"Balancer not found: {cfg.application.portfolio.balancer!r}")

    pipeline_config = build_pipeline_config(cfg)
    print(f"[models] pipeline={[st.name for st in pipeline_config.stages]}")

    def step_once() -> None:
        # 1) Structural universe from coverage + ensure held symbols are included
        coverage = build_coverage(cfg, pipeline_service.market_data, universe)
        portfolio = _build_portfolio_snapshot(account)
        held_symbols = set(portfolio.positions.keys())
        universe_symbols = sorted(set(coverage) | held_symbols)
        print(f"[coverage] {len(universe_symbols)} symbols -> {universe_symbols}")

        # 2) Run pipeline (single entrypoint)
        result = pipeline_service.run(
            universe_symbols=universe_symbols,
            portfolio_snapshot=portfolio,
            pipeline_config=pipeline_config,
        )

        if result.stage_stats:
            print(f"[pipeline] stage_stats={result.stage_stats}")

        # 3) Allocation -> target weights
        target_alloc = allocator.allocate(result.signals_by_symbol)

        # 4) Balancing -> rebalance plan
        plan = balancer.plan(
            portfolio=portfolio,
            target=target_alloc,
            threshold=cfg.application.portfolio.threshold_weight,
        )
        print(f"[rebalance] plan={len(plan)} instructions")

        # 5) Orders -> execution
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
