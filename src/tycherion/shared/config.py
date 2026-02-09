from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional, Any
import os, yaml
from dotenv import load_dotenv

class Trading(BaseModel):
    dry_run: bool = True
    require_demo: bool = True
    deviation_points: int = 10
    volume_mode: str = "min"     # 'min' | 'fixed'
    fixed_volume: float = 0.01

class Risk(BaseModel):
    risk_per_trade_pct: float = 0.5
    max_daily_loss_pct: float = 2.0

class MT5(BaseModel):
    terminal_path: Optional[str] = None
    server: Optional[str] = None
    login: Optional[int] = None
    password: Optional[str] = None

class RunMode(BaseModel):
    name: str = "live_multimodel"

class ScheduleCfg(BaseModel):
    run_forever: bool = False
    interval_seconds: int = 60

class CoverageCfg(BaseModel):
    source: str = "market_watch"
    symbols: list[str] = []
    pattern: str | None = None


class PipelineStageCfg(BaseModel):
    """Configuration of a single stage in the model pipeline."""

    name: str
    drop_threshold: float | None = None


class ModelsCfg(BaseModel):
    """Application-level model selection.

    `pipeline` defines an ordered list of models to run per symbol. The order
    is the order of execution. Each stage can optionally define a
    `drop_threshold` used to discard non-held symbols early.
    """

    pipeline: list[PipelineStageCfg] = []

    @field_validator("pipeline", mode="before")
    @classmethod
    def _coerce_pipeline(cls, v: Any):
        # Accept both:
        # - pipeline: ["trend_following", "mean_reversion"]
        # - pipeline: [{name: "...", drop_threshold: ...}, ...]
        if v is None:
            return []
        if isinstance(v, list):
            out: list[Any] = []
            for item in v:
                if isinstance(item, str):
                    out.append({"name": item})
                else:
                    out.append(item)
            return out
        return v


class PortfolioCfg(BaseModel):
    allocator: str = "proportional"     # plugin name
    balancer: str = "threshold"         # plugin name
    threshold_weight: float = 0.25      # only rebalance if |w| >= threshold

class ApplicationCfg(BaseModel):
    run_mode: RunMode = RunMode()
    playbook: str = "default"
    schedule: ScheduleCfg = ScheduleCfg()
    coverage: CoverageCfg = CoverageCfg()
    models: ModelsCfg = ModelsCfg()
    portfolio: PortfolioCfg = PortfolioCfg()


class TelemetrySinkCfg(BaseModel):
    enabled: bool = True
    channels: list[str] = ["audit", "ops"]
    min_level: str = "INFO"  # DEBUG/INFO/WARN/ERROR


class TelemetryCfg(BaseModel):
    """Telemetry configuration (bootstrap/application concern, not domain).

    Notes about the two databases we plan to have in Tycherion:
    - PostgreSQL: for *analytics* and structured datasets (models, indicators, actions, etc.).
      The schema for this is not defined yet.
    - MongoDB: for *operational health / audit journal* (telemetry events, errors, spans, etc.).

    Right now this config focuses on telemetry sinks (journal-like append-only storage).
    """

    # PostgreSQL execution journal (optional)
    db_enabled: bool = True
    # PostgreSQL DSN, e.g. "postgresql://user:pass@host:5432/dbname"
    db_dsn: Optional[str] = None
    db_channels: list[str] = ["audit", "ops"]
    db_min_level: str = "INFO"
    db_batch_size: int = 50

    # MongoDB execution journal (optional)
    mongo_enabled: bool = False
    # Mongo URI, e.g. "mongodb://user:pass@host:27017/?authSource=admin"
    mongo_uri: Optional[str] = None
    mongo_db: str = "tycherion"
    mongo_collection: str = "ops_journal"
    mongo_channels: list[str] = ["audit", "ops"]
    mongo_min_level: str = "INFO"
    mongo_batch_size: int = 200

    # Console sink
    console_enabled: bool = False
    console_channels: list[str] = ["ops"]
    console_min_level: str = "INFO"

    # OTLP export (optional; prepared for Alloy/Collector fan-out)
    otlp_enabled: bool = False
    otlp_endpoint: str = "http://localhost:4317"



class AppConfig(BaseModel):
    timeframe: str
    lookback_days: int
    trading: Trading = Trading()
    risk: Risk = Risk()
    mt5: MT5 = MT5()
    application: ApplicationCfg = ApplicationCfg()
    telemetry: TelemetryCfg = TelemetryCfg()

def load_config(path: str) -> AppConfig:
    load_dotenv(override=False)
    import pathlib
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    raw.setdefault("mt5", {})
    mt5_cfg = raw["mt5"] or {}

    def coalesce(yaml_val, env_val):
        return env_val if (yaml_val in (None, "", 0) and env_val not in (None, "")) else yaml_val

    env_terminal = os.getenv("MT5_TERMINAL_PATH")
    env_server   = os.getenv("MT5_SERVER")
    env_login    = os.getenv("MT5_LOGIN")
    env_pass     = os.getenv("MT5_PASSWORD")

    mt5_cfg["terminal_path"] = coalesce(mt5_cfg.get("terminal_path"), env_terminal)
    mt5_cfg["server"]        = coalesce(mt5_cfg.get("server"),        env_server)
    mt5_cfg["login"]         = coalesce(mt5_cfg.get("login"),         int(env_login) if env_login and env_login.isdigit() else None)
    mt5_cfg["password"]      = coalesce(mt5_cfg.get("password"),      env_pass)


    # Observability/Telemetry env overrides (kept here to avoid leaking infra details into domain/application)
    raw.setdefault("telemetry", {})
    tel_cfg = raw["telemetry"] or {}

    def env_bool(name: str) -> bool | None:
        v = os.getenv(name)
        if v is None:
            return None
        v = str(v).strip().lower()
        if v in ("1", "true", "yes", "y", "on"):
            return True
        if v in ("0", "false", "no", "n", "off"):
            return False
        return None

    def env_override(yaml_val, env_val):
        return env_val if env_val is not None else yaml_val

    tel_cfg["otlp_enabled"] = env_override(tel_cfg.get("otlp_enabled"), env_bool("TYCHERION_OTLP_ENABLED"))
    tel_cfg["otlp_endpoint"] = env_override(tel_cfg.get("otlp_endpoint"), os.getenv("TYCHERION_OTLP_ENDPOINT"))

    # Mongo ops journal (audit). Env keys are intentionally explicit.
    tel_cfg["mongo_enabled"] = env_override(tel_cfg.get("mongo_enabled"), env_bool("TYCHERION_MONGO_AUDIT_ENABLED"))
    tel_cfg["mongo_uri"] = env_override(tel_cfg.get("mongo_uri"), os.getenv("TYCHERION_MONGO_URI"))
    tel_cfg["mongo_db"] = env_override(tel_cfg.get("mongo_db"), os.getenv("TYCHERION_MONGO_DB"))
    tel_cfg["mongo_collection"] = env_override(tel_cfg.get("mongo_collection"), os.getenv("TYCHERION_MONGO_COLLECTION"))

    # Console output for local dev
    tel_cfg["console_enabled"] = env_override(tel_cfg.get("console_enabled"), env_bool("TYCHERION_CONSOLE_ENABLED"))
    tel_cfg["console_min_level"] = env_override(tel_cfg.get("console_min_level"), os.getenv("TYCHERION_CONSOLE_MIN_LEVEL"))

    raw["telemetry"] = tel_cfg

    raw["mt5"] = mt5_cfg
    return AppConfig.model_validate(raw)
