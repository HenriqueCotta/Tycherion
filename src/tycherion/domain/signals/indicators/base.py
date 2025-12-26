from __future__ import annotations

from abc import ABC, abstractmethod
import pandas as pd

from tycherion.domain.signals.entities import IndicatorOutput


class BaseIndicator(ABC):
    """Abstract base class for indicator plugins."""

    # Set by decorator
    key: str = ""
    method: str = ""
    tags: set[str] = set()

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> IndicatorOutput:
        raise NotImplementedError
