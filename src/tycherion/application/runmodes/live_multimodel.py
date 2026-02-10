from __future__ import annotations

import hashlib
import json
import time
from typing import Dict

from tycherion.shared.config import AppConfig
from tycherion.ports.trading import TradingPort
from tycherion.ports.account import AccountPort
from tycherion.ports.universe import UniversePort

from tycherion.ports.observability import semconv
from tycherion.ports.observability.observability import ObservabilityPort
from tycherion.ports.observability.types import Severity, TYCHERION_SCHEMA_VERSION

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


def _stable_config_hash(d: dict) -> str:
    try:
        blob = json.dumps(d, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]
    except Exception:
        return ""


def run_live_multimodel(
    cfg: AppConfig,
    trader: TradingPort,
    account: AccountPort,
    universe: UniversePort,
    pipeline_service: ModelPipelineService,
    *,
    observability: ObservabilityPort,
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

    tracer = observability.traces.get_tracer("tycherion.runmodes.live_multimodel", version=TYCHERION_SCHEMA_VERSION)
    logger = observability.logs.get_logger("tycherion.runmodes.live_multimodel", version=TYCHERION_SCHEMA_VERSION)

    def step_once() -> None:
        cfg_hash = _stable_config_hash(cfg.model_dump())

        with tracer.start_as_current_span(
            semconv.SPAN_RUN,
            attributes={
                semconv.ATTR_RUN_MODE: "live_multimodel",
                "timeframe": cfg.timeframe,
                "lookback_days": int(cfg.lookback_days),
                "pipeline_stages": [st.name for st in pipeline_config.stages],
                semconv.ATTR_CONFIG_HASH: cfg_hash,
                semconv.ATTR_CONFIG_PATH: config_path,
            },
        ) as span_run:
            try:
                # 1) Structural universe from coverage + ensure held symbols are included
                with tracer.start_as_current_span(semconv.SPAN_COVERAGE_FETCH) as span_cov:
                    coverage = build_coverage(cfg, pipeline_service.market_data, universe)
                    portfolio = _build_portfolio_snapshot(account)
                    held_symbols = set(portfolio.positions.keys())
                    universe_symbols = sorted(set(coverage) | held_symbols)

                    span_cov.add_event(
                        semconv.EVT_COVERAGE_SUMMARY,
                        {
                            "symbols_count": int(len(universe_symbols)),
                            "symbols_sample": universe_symbols[: min(10, len(universe_symbols))],
                        },
                    )

                # 2) Run pipeline (single entrypoint)
                result = pipeline_service.run(
                    universe_symbols=universe_symbols,
                    portfolio_snapshot=portfolio,
                    pipeline_config=pipeline_config,
                    observability=observability,
                )

                span_run.add_event(
                    semconv.EVT_PIPELINE_RUN_SUMMARY,
                    {f"stage_stats.{k}": int(v) for k, v in (result.stage_stats or {}).items()},
                )

                # 3) Allocation -> target weights
                with tracer.start_as_current_span(semconv.SPAN_ALLOCATOR) as span_alloc:
                    target_alloc = allocator.allocate(result.signals_by_symbol)
                    span_alloc.add_event(semconv.EVT_ALLOCATOR_COMPLETED, {"symbols_count": int(len(result.signals_by_symbol))})

                # 4) Balancing -> rebalance plan
                with tracer.start_as_current_span(semconv.SPAN_BALANCER) as span_bal:
                    plan = balancer.plan(
                        portfolio=portfolio,
                        target=target_alloc,
                        threshold=cfg.application.portfolio.threshold_weight,
                    )
                    span_bal.add_event(semconv.EVT_REBALANCE_PLAN_BUILT, {"instructions_count": int(len(plan))})

                # 5) Orders -> execution
                with tracer.start_as_current_span(semconv.SPAN_EXECUTION) as span_exec:
                    orders = build_orders(portfolio, plan, cfg.trading)
                    span_exec.add_event(semconv.EVT_ORDERS_BUILT, {"orders_count": int(len(orders))})

                    for od in orders:
                        if od.side.upper() == "BUY":
                            res = trader.market_buy(od.symbol, volume=od.volume)
                        else:
                            res = trader.market_sell(od.symbol, volume=od.volume)

                        logger.emit(
                            "trade.executed",
                            Severity.INFO,
                            {
                                semconv.ATTR_CHANNEL: "ops",
                                "symbol": od.symbol,
                                "side": od.side,
                                "volume": float(od.volume),
                                "result": str(res),
                            },
                        )

                span_run.set_status_ok()
            except BaseException as e:
                span_run.record_exception(e)
                span_run.set_status_error(str(e))
                logger.emit(
                    "run.exception",
                    Severity.ERROR,
                    {
                        semconv.ATTR_CHANNEL: "ops",
                        "run_mode": "live_multimodel",
                        "exception_type": type(e).__name__,
                        "message": str(e),
                    },
                )
                raise

    if cfg.application.schedule.run_forever:
        while True:
            try:
                step_once()
                time.sleep(max(1, cfg.application.schedule.interval_seconds))
            except KeyboardInterrupt:
                logger.emit(
                    "run.stopped",
                    Severity.INFO,
                    {
                        semconv.ATTR_CHANNEL: "ops",
                        "run_mode": "live_multimodel",
                        "reason": "KeyboardInterrupt",
                    },
                )
                break
            except Exception as e:
                # Error already recorded inside the run span, but keep a top-level log too.
                logger.emit(
                    "run.loop_exception",
                    Severity.ERROR,
                    {
                        semconv.ATTR_CHANNEL: "ops",
                        "run_mode": "live_multimodel",
                        "exception_type": type(e).__name__,
                        "message": str(e),
                    },
                )
                time.sleep(3)
    else:
        step_once()
