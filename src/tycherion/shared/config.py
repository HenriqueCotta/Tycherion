from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
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
    top_n: int = 20

class PortfolioCfg(BaseModel):
    allocator: str = "proportional"     # plugin name
    balancer: str = "threshold"         # plugin name
    threshold_weight: float = 0.25      # only rebalance if |w| >= threshold

class ApplicationCfg(BaseModel):
    run_mode: RunMode = RunMode()
    playbook: str = "default"
    schedule: ScheduleCfg = ScheduleCfg()
    coverage: CoverageCfg = CoverageCfg()
    portfolio: PortfolioCfg = PortfolioCfg()

class AppConfig(BaseModel):
    timeframe: str
    lookback_days: int
    trading: Trading = Trading()
    risk: Risk = Risk()
    mt5: MT5 = MT5()
    application: ApplicationCfg = ApplicationCfg()

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

    raw["mt5"] = mt5_cfg
    return AppConfig.model_validate(raw)
