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
from tycherion.application.telemetry import TraceTelemetry, new_trace_id, stable_config_hash
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
    config_path: str | None = None,
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
        trace_id = new_trace_id()
        t = TraceTelemetry(port=telemetry, trace_id=trace_id, base_attributes={"component": "runmode"})

        try:
            cfg_hash = stable_config_hash(cfg.model_dump())
        except Exception:
            cfg_hash = ""

        with t.span(
            "run",
            channel="ops",
            level=TelemetryLevel.INFO,
            attributes={"run_mode": "live_multimodel"},
            data={
                "timeframe": cfg.timeframe,
                "lookback_days": int(cfg.lookback_days),
                "pipeline_stages": [st.name for st in pipeline_config.stages],
                "config_hash": cfg_hash,
                "config_path": config_path,
            },
        ):

        # 1) Structural universe from coverage + ensure held symbols are included
            with t.span("coverage.fetch", channel="ops", level=TelemetryLevel.INFO):
                coverage = build_coverage(cfg, pipeline_service.market_data, universe)
                portfolio = _build_portfolio_snapshot(account)
                held_symbols = set(portfolio.positions.keys())
                universe_symbols = sorted(set(coverage) | held_symbols)

                t.emit(
                    name="coverage.summary",
                    channel="ops",
                    level=TelemetryLevel.INFO,
                    data={
                        "symbols_count": int(len(universe_symbols)),
                        "symbols_sample": universe_symbols[: min(10, len(universe_symbols))],
                    },
                )

        # 2) Run pipeline (single entrypoint)
            result = pipeline_service.run(
                universe_symbols=universe_symbols,
                portfolio_snapshot=portfolio,
                pipeline_config=pipeline_config,
                tracer=t,
            )

            t.emit(
                name="pipeline.run_summary",
                channel="ops",
                level=TelemetryLevel.INFO,
                data={"stage_stats": dict(result.stage_stats or {})},
            )

        # 3) Allocation -> target weights
            with t.span("allocator", channel="ops", level=TelemetryLevel.INFO):
                target_alloc = allocator.allocate(result.signals_by_symbol)

        # 4) Balancing -> rebalance plan
            with t.span("balancer", channel="ops", level=TelemetryLevel.INFO):
                plan = balancer.plan(
                    portfolio=portfolio,
                    target=target_alloc,
                    threshold=cfg.application.portfolio.threshold_weight,
                )
                t.emit(
                    name="rebalance.plan_built",
                    channel="ops",
                    level=TelemetryLevel.INFO,
                    data={"instructions_count": int(len(plan))},
                )

        # 5) Orders -> execution
            with t.span("execution", channel="ops", level=TelemetryLevel.INFO):
                orders = build_orders(portfolio, plan, cfg.trading)
                t.emit(
                    name="orders.built",
                    channel="ops",
                    level=TelemetryLevel.INFO,
                    data={"orders_count": int(len(orders))},
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
                        attributes={"symbol": od.symbol},
                        data={"side": od.side, "volume": float(od.volume), "result": str(res)},
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
                t = TraceTelemetry(port=telemetry, trace_id="bootstrap", base_attributes={"component": "runmode"})
                t.emit(
                    name="run.stopped",
                    channel="ops",
                    level=TelemetryLevel.INFO,
                    attributes={"run_mode": "live_multimodel"},
                    data={"reason": "KeyboardInterrupt"},
                )
                break
            except Exception as e:
                t = TraceTelemetry(port=telemetry, trace_id="bootstrap", base_attributes={"component": "runmode"})
                t.emit(
                    name="error.exception",
                    channel="ops",
                    level=TelemetryLevel.ERROR,
                    attributes={"run_mode": "live_multimodel"},
                    data={"exception_type": type(e).__name__, "message": str(e)},
                )
                time.sleep(3)
    else:
        step_once()

