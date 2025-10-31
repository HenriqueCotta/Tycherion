from __future__ import annotations
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5

from tycherion.shared.config import AppConfig
from tycherion.application.usecases.loop_engine import LoopPolicy, run_loop
from tycherion.application.services.watchlist_service import build_watchlist
from tycherion.ports.market_data import MarketDataPort
from tycherion.ports.trading import TradingPort
from tycherion.ports.account import AccountPort
from tycherion.ports.watchlist import WatchlistPort
from tycherion.domain.strategies.sma_cross import sma_cross_signal

def _make_step(cfg: AppConfig, data: MarketDataPort, trader: TradingPort, account: AccountPort, watchlist: WatchlistPort):
    watchList = build_watchlist(cfg, data, watchlist)
    fast = cfg.strategy.sma_cross.fast_period
    slow = cfg.strategy.sma_cross.slow_period

    def step():
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=cfg.lookback_days)

        for symbol in watchList:
            if not mt5.symbol_select(symbol, True):
                print(f"[{symbol}] indisponível no terminal.")
                continue

            df = data.get_bars(symbol, cfg.timeframe, start, end)
            if df.empty:
                print(f"[{symbol}] sem dados.")
                continue

            decision = sma_cross_signal(df, fast, slow)
            last_close = float(df['close'].iloc[-1])
            sma_f = float(df['sma_fast'].iloc[-1])
            sma_s = float(df['sma_slow'].iloc[-1])
            print(f"[{symbol}] close={last_close:.5f} SMA{fast}={sma_f:.5f} SMA{slow}={sma_s:.5f} -> {decision}")

            if decision == "BUY":
                trader.market_buy(symbol)
            elif decision == "EXIT":
                trader.market_sell(symbol)
    return step

def run_usecase_sma_cross(cfg: AppConfig, data: MarketDataPort, trader: TradingPort, account: AccountPort, watchlist: WatchlistPort) -> None:
    policy = LoopPolicy(
        run_forever=cfg.application.scan.run_forever,
        interval_seconds=cfg.application.scan.interval_seconds,
    )
    
    step = _make_step(cfg, data, trader, account, watchlist)
    run_loop(step, policy)
