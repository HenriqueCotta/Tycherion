from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from tycherion.domain.portfolio.entities import SignalsBySymbol
from tycherion.domain.signals.entities import SymbolState

from .config import PipelineConfig


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    pipeline_config: PipelineConfig
    states_by_symbol: Dict[str, SymbolState]
    signals_by_symbol: SignalsBySymbol
    stage_stats: Dict[str, int]
