from __future__ import annotations
import MetaTrader5 as mt5
from tycherion.shared.config import load_config, AppConfig
from tycherion.adapters.mt5.market_data_mt5 import MT5MarketData
from tycherion.adapters.mt5.trading_mt5 import MT5Trader
from tycherion.adapters.mt5.account_mt5 import MT5Account
from tycherion.adapters.mt5.universe_mt5 import MT5Universe
from tycherion.application.runmodes.live_multimodel import run_live_multimodel
from tycherion.application.plugins import registry as _registry

def _ensure_initialized(cfg: AppConfig) -> None:
    if not mt5.initialize(path=cfg.mt5.terminal_path or None):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    if cfg.mt5.login and cfg.mt5.password and cfg.mt5.server:
        if not mt5.login(login=int(cfg.mt5.login), password=cfg.mt5.password, server=cfg.mt5.server):
            raise SystemExit(f"MT5 login failed: {mt5.last_error()}")

def _assert_account_ok(cfg: AppConfig) -> None:
    ai = mt5.account_info()
    if ai is None:
        raise SystemExit("No MT5 account logged in. Open the Terminal and login to DEMO.")
    if cfg.trading.require_demo and ai.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise SystemExit("Blocked: not a DEMO account. Enable DEMO or set require_demo=false.")

def run_app(config_path: str) -> None:
    cfg = load_config(config_path)
    _ensure_initialized(cfg)
    try:
        _assert_account_ok(cfg)
        _registry.auto_discover()
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
        name = (cfg.application.run_mode.name or '').lower()
        if name == 'live_multimodel':
            run_live_multimodel(cfg, market_data, trader, account, universe)
        else:
            raise SystemExit(f'Unknown run_mode: {name}')
    finally:
        mt5.shutdown()
