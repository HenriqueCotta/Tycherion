from __future__ import annotations

import os
import socket
from pathlib import Path

import MetaTrader5 as mt5

from tycherion.shared.config import load_config, AppConfig
from tycherion.adapters.mt5.market_data_mt5 import MT5MarketData
from tycherion.adapters.mt5.trading_mt5 import MT5Trader
from tycherion.adapters.mt5.account_mt5 import MT5Account
from tycherion.adapters.mt5.universe_mt5 import MT5Universe

from tycherion.adapters.telemetry.db_journal import DbExecutionJournalSink
from tycherion.adapters.telemetry.mongo_journal import MongoExecutionJournalSink
from tycherion.adapters.telemetry.console import ConsoleTelemetrySink

from tycherion.application.telemetry import TelemetryHub, TelemetryProvider
from tycherion.ports.telemetry import TelemetryLevel

from tycherion.application.plugins import registry as _registry
from tycherion.application.pipeline.service import ModelPipelineService
from tycherion.application.runmodes.live_multimodel import run_live_multimodel


def _ensure_initialized(cfg: AppConfig) -> None:
    if not mt5.initialize(path=cfg.mt5.terminal_path or None):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    if cfg.mt5.login and cfg.mt5.password and cfg.mt5.server:
        if not mt5.login(
            login=int(cfg.mt5.login),
            password=cfg.mt5.password,
            server=cfg.mt5.server,
        ):
            raise SystemExit(f"MT5 login failed: {mt5.last_error()}")


def run_app(config_path: str) -> None:
    cfg = load_config(config_path)

    # Telemetry must be available as early as possible (e.g. plugin discovery).
    provider = _build_telemetry(cfg, config_path)

    # Discover all indicators, models, allocators and balancers
    bootstrap_tracer = provider.new_trace(base_attributes={"component": "bootstrap"})
    with bootstrap_tracer.span("bootstrap.discover", channel="ops", level=TelemetryLevel.INFO):
        _registry.auto_discover(bootstrap_tracer)

    _ensure_initialized(cfg)
    try:
        market_data = MT5MarketData()
        trader = MT5Trader(
            dry_run=cfg.trading.dry_run,
            require_demo=cfg.trading.require_demo,
            deviation_points=cfg.trading.deviation_points,
            volume_mode=cfg.trading.volume_mode,
            fixed_volume=cfg.trading.fixed_volume,
        )
        account = MT5Account()
        universe = MT5Universe()

        pipeline_service = ModelPipelineService(
            market_data=market_data,
            model_registry=_registry.MODELS,
            indicator_picker=_registry.pick_indicator_for,
            timeframe=cfg.timeframe,
            lookback_days=cfg.lookback_days,
            playbook=cfg.application.playbook,
        )

        run_mode = (cfg.application.run_mode.name or "").lower()
        if run_mode == "live_multimodel":
            run_live_multimodel(
                cfg,
                trader,
                account,
                universe,
                pipeline_service,
                telemetry_provider=provider,
                config_path=config_path,
            )
        else:
            raise SystemExit(f"Unknown run_mode: {run_mode}")
    finally:
        try:
            provider.close()
        except Exception:
            pass
        mt5.shutdown()


def _build_telemetry(cfg: AppConfig, config_path: str) -> TelemetryProvider:
    _ = config_path

    runner_id = (os.getenv("TYCHERION_RUNNER_ID") or "").strip()
    if not runner_id:
        # Fallback: still deterministic enough for local dev.
        runner_id = f"runner-{socket.gethostname()}-{os.getpid()}"

    sinks = []
    telemetry_cfg = cfg.telemetry

    if bool(telemetry_cfg.db_enabled) and bool(telemetry_cfg.db_dsn):
        sinks.append(
            DbExecutionJournalSink(
                dsn=str(telemetry_cfg.db_dsn),
                enabled_flag=True,
                channels=set(telemetry_cfg.db_channels or ["audit", "ops"]),
                min_level=TelemetryLevel.coerce(telemetry_cfg.db_min_level),
                batch_size=int(telemetry_cfg.db_batch_size or 50),
            )
        )

    if bool(telemetry_cfg.mongo_enabled) and bool(telemetry_cfg.mongo_uri):
        sinks.append(
            MongoExecutionJournalSink(
                uri=str(telemetry_cfg.mongo_uri),
                db_name=str(telemetry_cfg.mongo_db or "tycherion"),
                collection_name=str(telemetry_cfg.mongo_collection or "execution_journal_events"),
                enabled_flag=True,
                channels=set(telemetry_cfg.mongo_channels or ["audit", "ops"]),
                min_level=TelemetryLevel.coerce(telemetry_cfg.mongo_min_level),
                batch_size=int(telemetry_cfg.mongo_batch_size or 200),
            )
        )

    if bool(telemetry_cfg.console_enabled):
        sinks.append(
            ConsoleTelemetrySink(
                enabled_flag=True,
                channels=set(telemetry_cfg.console_channels or ["ops"]),
                min_level=TelemetryLevel.coerce(telemetry_cfg.console_min_level),
            )
        )

    hub = TelemetryHub(sinks=sinks)
    return TelemetryProvider(runner_id=runner_id, hub=hub)
