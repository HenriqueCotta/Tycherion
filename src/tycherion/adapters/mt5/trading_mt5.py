from __future__ import annotations
from dataclasses import dataclass
import MetaTrader5 as mt5
from tycherion.ports.trading import TradingPort, TradeResult
from tycherion.shared.decorators import demo_only, logged

@dataclass
class MT5Trader(TradingPort):
    dry_run: bool = True
    require_demo: bool = True
    deviation_points: int = 10
    volume_mode: str = "min"       # "min" | "fixed"
    fixed_volume: float = 0.01

    def _symbol_min_volume(self, symbol: str) -> float:
        info = mt5.symbol_info(symbol)
        if not info:
            raise RuntimeError(f"Symbol info not found: {symbol}")
        v = max(info.volume_min, info.volume_step)
        steps = round(v / info.volume_step)
        return steps * info.volume_step

    def _volume(self, symbol: str) -> float:
        if self.volume_mode == "fixed":
            return float(self.fixed_volume)
        return self._symbol_min_volume(symbol)

    @logged
    @demo_only
    def market_buy(self, symbol: str) -> TradeResult:
        if self.dry_run:
            return TradeResult(True, 0, None, "DRY_RUN: buy skipped")
        if not mt5.symbol_select(symbol, True):
            return TradeResult(False, -1, None, f"symbol_select failed: {symbol}")
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return TradeResult(False, -2, None, "missing tick")
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "type": mt5.ORDER_TYPE_BUY,
            "volume": self._volume(symbol),
            "price": tick.ask,
            "deviation": self.deviation_points,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
            "magic": 201,
            "comment": "tycherion-buy",
        }
        check = mt5.order_check(request)
        if not check or check.retcode != mt5.TRADE_RETCODE_DONE:
            return TradeResult(False, getattr(check, "retcode", -3), None, f"order_check failed: {check}")
        res = mt5.order_send(request)
        ok = bool(res and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED))
        return TradeResult(ok, getattr(res, "retcode", -4), getattr(res, "order", None), str(res))

    @logged
    @demo_only
    def market_sell(self, symbol: str) -> TradeResult:
        if self.dry_run:
            return TradeResult(True, 0, None, "DRY_RUN: sell skipped")
        if not mt5.symbol_select(symbol, True):
            return TradeResult(False, -1, None, f"symbol_select failed: {symbol}")
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return TradeResult(False, -2, None, "missing tick")
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "type": mt5.ORDER_TYPE_SELL,
            "volume": self._volume(symbol),
            "price": tick.bid,
            "deviation": self.deviation_points,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
            "magic": 201,
            "comment": "tycherion-sell",
        }
        check = mt5.order_check(request)
        if not check or check.retcode != mt5.TRADE_RETCODE_DONE:
            return TradeResult(False, getattr(check, "retcode", -3), None, f"order_check failed: {check}")
        res = mt5.order_send(request)
        ok = bool(res and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED))
        return TradeResult(ok, getattr(res, "retcode", -4), getattr(res, "order", None), str(res))
