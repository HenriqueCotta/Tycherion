from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NewType

Symbol = NewType("Symbol", str)


class AssetClass(str, Enum):
    EQUITY = "equity"
    FUTURE = "future"
    FX = "fx"
    OTHER = "other"


@dataclass
class Instrument:
    """Domain representation of a tradable instrument (stock, future, FX, etc.)."""

    symbol: Symbol
    asset_class: AssetClass
    currency: str
    lot_size: float
    min_volume: float
    volume_step: float


@dataclass
class Bar:
    """Minimal OHLCV bar used by indicators and models when not using DataFrame."""

    symbol: Symbol
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
