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


class ObservabilityCfg(BaseModel):
    """Observability/OTel configuration used by bootstrap/application."""

    # Console sink (dev)
    console_enabled: bool = False
    console_channels: list[str] = ["ops"]
    console_min_level: str = "INFO"
    log_format: str = "pretty"  # pretty | json

    # OTLP export (Collector/Alloy)
    otlp_enabled: bool = False
    otlp_endpoint: str = "http://localhost:4317"
    otlp_protocol: str = "grpc"  # grpc|http
    otlp_headers: str | None = None
    otlp_insecure: bool | None = None  # None => infer from scheme

    # Deployment metadata
    deployment_env: str | None = None



class AppConfig(BaseModel):
    timeframe: str
    lookback_days: int
    trading: Trading = Trading()
    risk: Risk = Risk()
    mt5: MT5 = MT5()
    application: ApplicationCfg = ApplicationCfg()
    observability: ObservabilityCfg = ObservabilityCfg()
    telemetry: ObservabilityCfg | None = None  # backward compat

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


    # Observability env overrides (kept here to avoid leaking infra details into domain/application)
    # Support legacy 'telemetry' key as alias.
    raw.setdefault("observability", raw.get({}))
    obs_cfg = raw["observability"] or {}

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

    obs_cfg["otlp_enabled"] = env_override(obs_cfg.get("otlp_enabled"), env_bool("TYCHERION_OTLP_ENABLED"))
    obs_cfg["otlp_endpoint"] = env_override(obs_cfg.get("otlp_endpoint"), os.getenv("TYCHERION_OTLP_ENDPOINT"))
    obs_cfg["otlp_protocol"] = env_override(obs_cfg.get("otlp_protocol"), os.getenv("TYCHERION_OTLP_PROTOCOL"))
    obs_cfg["otlp_headers"] = env_override(obs_cfg.get("otlp_headers"), os.getenv("TYCHERION_OTLP_HEADERS"))
    obs_cfg["otlp_insecure"] = env_override(obs_cfg.get("otlp_insecure"), env_bool("TYCHERION_OTLP_INSECURE"))
    obs_cfg["deployment_env"] = env_override(obs_cfg.get("deployment_env"), os.getenv("TYCHERION_DEPLOYMENT_ENV"))
    obs_cfg["log_format"] = env_override(obs_cfg.get("log_format"), os.getenv("TYCHERION_LOG_FORMAT"))

    # Console output for local dev
    obs_cfg["console_enabled"] = env_override(obs_cfg.get("console_enabled"), env_bool("TYCHERION_CONSOLE_ENABLED"))
    obs_cfg["console_min_level"] = env_override(obs_cfg.get("console_min_level"), os.getenv("TYCHERION_CONSOLE_MIN_LEVEL"))
    obs_cfg["console_channels"] = env_override(obs_cfg.get("console_channels"), obs_cfg.get("console_channels"))

    raw["observability"] = obs_cfg
    if "telemetry" in raw and raw["telemetry"] and "observability" not in raw:
        print("[tycherion] WARNING: 'telemetry' config is deprecated; use 'observability'.")

    raw["mt5"] = mt5_cfg
    return AppConfig.model_validate(raw)
