from __future__ import annotations

import os
import socket

import MetaTrader5 as mt5

from tycherion.shared.config import load_config, AppConfig
from tycherion.adapters.mt5.market_data_mt5 import MT5MarketData
from tycherion.adapters.mt5.trading_mt5 import MT5Trader
from tycherion.adapters.mt5.account_mt5 import MT5Account
from tycherion.adapters.mt5.universe_mt5 import MT5Universe

from tycherion.adapters.observability.noop.noop_observability import NoopObservability

from tycherion.ports.observability.observability import ObservabilityPort
from tycherion.ports.observability.types import Severity, TYCHERION_SCHEMA_VERSION

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

    # Observability must be available as early as possible (e.g. plugin discovery).
    obs = _build_observability(cfg, config_path)

    tracer = obs.traces.get_tracer("tycherion.bootstrap", version=TYCHERION_SCHEMA_VERSION)
    logger = obs.logs.get_logger("tycherion.bootstrap", version=TYCHERION_SCHEMA_VERSION)

    with tracer.start_as_current_span("bootstrap.discover", attributes={"component": "bootstrap"}):
        _registry.auto_discover(observability=obs)
        logger.emit("Plugin discovery completed", Severity.INFO, {"tycherion.channel": "ops"})

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
                observability=obs,
                config_path=config_path,
            )
        else:
            raise SystemExit(f"Unknown run_mode: {run_mode}")
    finally:
        try:
            obs.shutdown()
        except Exception:
            pass
        mt5.shutdown()


def _parse_severity(level: str | None) -> Severity:
    lvl = (level or "INFO").strip().upper()
    try:
        return Severity[lvl]
    except Exception:
        # Accept legacy values too
        if lvl in ("WARNING",):
            return Severity.WARN
        return Severity.INFO


def _build_observability(cfg: AppConfig, config_path: str) -> ObservabilityPort:
    _ = config_path

    runner_id = (os.getenv("TYCHERION_RUNNER_ID") or "").strip()
    if not runner_id:
        # Fallback: deterministic enough for local dev.
        runner_id = f"runner-{socket.gethostname()}-{os.getpid()}"

    tel = cfg.telemetry

    try:
        from tycherion.adapters.observability.otel.otel_observability import (
            OtelObservability,
            OtelObservabilityConfig,
        )

        return OtelObservability(
            OtelObservabilityConfig(
                runner_id=runner_id,
                schema_version=TYCHERION_SCHEMA_VERSION,
                console_enabled=bool(tel.console_enabled),
                console_min_severity=_parse_severity(tel.console_min_level),
                console_show_span_lifecycle=True,
                otlp_enabled=bool(getattr(tel, "otlp_enabled", False)),
                otlp_endpoint=str(getattr(tel, "otlp_endpoint", "http://localhost:4317") or "http://localhost:4317"),
                mongo_audit_enabled=bool(tel.mongo_enabled),
                mongo_uri=str(tel.mongo_uri) if tel.mongo_uri else None,
                mongo_db=str(tel.mongo_db or "tycherion"),
                mongo_collection=str(tel.mongo_collection or "ops_journal"),
                mongo_min_severity=_parse_severity(tel.mongo_min_level),
                mongo_batch_size=int(tel.mongo_batch_size or 200),
            )
        )
    except Exception as e:
        # Hard-fail would be annoying during local dev if deps are missing, so we degrade to noop.
        print(f"[tycherion] Observability disabled (failed to init OTel adapter): {e}")
        return NoopObservability()
