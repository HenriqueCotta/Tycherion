from __future__ import annotations

import MetaTrader5 as mt5
from pathlib import Path

from tycherion.shared.config import load_config, AppConfig
from tycherion.adapters.mt5.market_data_mt5 import MT5MarketData
from tycherion.adapters.mt5.trading_mt5 import MT5Trader
from tycherion.adapters.mt5.account_mt5 import MT5Account
from tycherion.adapters.mt5.universe_mt5 import MT5Universe

from tycherion.adapters.telemetry.db_journal import DbExecutionJournalSink
from tycherion.adapters.telemetry.console import ConsoleTelemetrySink
from tycherion.application.telemetry.hub import TelemetryHub

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
    telemetry = _build_telemetry(cfg, config_path)

    # Discover all indicators, models, allocators and balancers
    _registry.auto_discover(telemetry)

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
            telemetry=telemetry,
        )

        run_mode = (cfg.application.run_mode.name or "").lower()
        if run_mode == "live_multimodel":
            run_live_multimodel(cfg, trader, account, universe, pipeline_service, telemetry=telemetry)
        else:
            raise SystemExit(f"Unknown run_mode: {run_mode}")
    finally:
        try:
            telemetry.close()
        except Exception:
            pass
        mt5.shutdown()

def _build_telemetry(cfg: AppConfig, config_path: str) -> TelemetryHub:
    sinks = []
    telemetry_cfg = cfg.telemetry


    if bool(telemetry_cfg.db_enabled):
        sinks.append(
            DbExecutionJournalSink(
                db_path=str(telemetry_cfg.db_path or ''),
                enabled_flag=True,
                channels=set(telemetry_cfg.db_channels or ["audit", "ops"]),
                min_level=telemetry_cfg.db_min_level,
                batch_size=int(telemetry_cfg.db_batch_size or 50),
            )
        )

    if bool(telemetry_cfg.console_enabled):
        sinks.append(
            ConsoleTelemetrySink(
                enabled_flag=True,
                channels=set(telemetry_cfg.console_channels or ["ops"]),
                min_level=telemetry_cfg.console_min_level,
            )
        )

    return TelemetryHub(sinks=sinks)

