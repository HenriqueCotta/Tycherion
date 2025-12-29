from __future__ import annotations

import time
import uuid
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
from tycherion.application.telemetry.run_context import RunTelemetry
from tycherion.ports.telemetry import TelemetryLevel, TelemetryPort


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
    telemetry: TelemetryPort | None = None,
) -> None:
    """Live runmode that delegates per-symbol pipeline execution to ModelPipelineService."""

    allocator = ALLOCATORS.get(cfg.application.portfolio.allocator)
    if not allocator:
        raise RuntimeError(f"Allocator not found: {cfg.application.portfolio.allocator!r}")

    balancer = BALANCERS.get(cfg.application.portfolio.balancer)
    if not balancer:
        raise RuntimeError(f"Balancer not found: {cfg.application.portfolio.balancer!r}")

    pipeline_config = build_pipeline_config(cfg)
    # no stdout by default; this is emitted via telemetry when sinks are enabled

    def step_once() -> None:
        run_id = str(uuid.uuid4())
        t = RunTelemetry(port=telemetry, run_id=run_id, base_scope={"component": "runmode"})
        start_t = time.perf_counter()

        t.emit(
            name="run.cycle_started",
            channel="ops",
            level=TelemetryLevel.INFO,
            scope={"run_mode": "live_multimodel"},
            payload={
                "timeframe": cfg.timeframe,
                "lookback_days": int(cfg.lookback_days),
                "pipeline": [st.name for st in pipeline_config.stages],
            },
        )

        # 1) Structural universe from coverage + ensure held symbols are included
        coverage = build_coverage(cfg, pipeline_service.market_data, universe)
        portfolio = _build_portfolio_snapshot(account)
        held_symbols = set(portfolio.positions.keys())
        universe_symbols = sorted(set(coverage) | held_symbols)

        t.emit(
            name="run.coverage_built",
            channel="ops",
            level=TelemetryLevel.INFO,
            payload={
                "symbols_count": int(len(universe_symbols)),
                "symbols_sample": universe_symbols[: min(10, len(universe_symbols))],
            },
        )

        # 2) Run pipeline (single entrypoint)
        result = pipeline_service.run(
            universe_symbols=universe_symbols,
            portfolio_snapshot=portfolio,
            pipeline_config=pipeline_config,
            run_id=run_id,
        )

        t.emit(
            name="run.pipeline_finished",
            channel="ops",
            level=TelemetryLevel.INFO,
            payload={"stage_stats": dict(result.stage_stats or {})},
        )

        # 3) Allocation -> target weights
        target_alloc = allocator.allocate(result.signals_by_symbol)

        # 4) Balancing -> rebalance plan
        plan = balancer.plan(
            portfolio=portfolio,
            target=target_alloc,
            threshold=cfg.application.portfolio.threshold_weight,
        )
        t.emit(
            name="rebalance.plan_built",
            channel="ops",
            level=TelemetryLevel.INFO,
            payload={"instructions_count": int(len(plan))},
        )

        # 5) Orders -> execution
        orders = build_orders(portfolio, plan, cfg.trading)
        t.emit(
            name="orders.built",
            channel="ops",
            level=TelemetryLevel.INFO,
            payload={"orders_count": int(len(orders))},
        )

        for od in orders:
            if od.side.upper() == "BUY":
                res = trader.market_buy(od.symbol, volume=od.volume)
            else:
                res = trader.market_sell(od.symbol, volume=od.volume)
            t.emit(
                name="trade.executed",
                channel="ops",
                level=TelemetryLevel.INFO,
                scope={"symbol": od.symbol},
                payload={"side": od.side, "volume": float(od.volume), "result": str(res)},
            )

        t.emit(
            name="run.cycle_finished",
            channel="ops",
            level=TelemetryLevel.INFO,
            scope={"run_mode": "live_multimodel"},
            payload={"duration_ms": int((time.perf_counter() - start_t) * 1000)},
        )

        flush = getattr(telemetry, "flush", None)
        if callable(flush):
            try:
                flush()
            except Exception:
                pass

    if cfg.application.schedule.run_forever:
        while True:
            try:
                step_once()
                time.sleep(max(1, cfg.application.schedule.interval_seconds))
            except KeyboardInterrupt:
                t = RunTelemetry(port=telemetry, run_id="bootstrap", base_scope={"component": "runmode"})
                t.emit(
                    name="run.stopped",
                    channel="ops",
                    level=TelemetryLevel.INFO,
                    scope={"run_mode": "live_multimodel"},
                    payload={"reason": "KeyboardInterrupt"},
                )
                break
            except Exception as e:
                t = RunTelemetry(port=telemetry, run_id="bootstrap", base_scope={"component": "runmode"})
                t.emit(
                    name="error.exception",
                    channel="ops",
                    level=TelemetryLevel.ERROR,
                    scope={"run_mode": "live_multimodel"},
                    payload={"exception_type": type(e).__name__, "message": str(e)},
                )
                time.sleep(3)
    else:
        step_once()

