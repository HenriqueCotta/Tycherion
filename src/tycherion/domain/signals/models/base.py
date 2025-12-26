from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from tycherion.domain.signals.entities import IndicatorOutput, ModelDecision


class SignalModel(ABC):
    """Abstract base class for per-symbol signal models."""

    name: str = ""
    tags: set[str] = set()

    @abstractmethod
    def requires(self) -> set[str]:
        raise NotImplementedError

    @abstractmethod
    def decide(self, indicators: Dict[str, IndicatorOutput]) -> ModelDecision:
        raise NotImplementedError
