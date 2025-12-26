from __future__ import annotations

from abc import ABC, abstractmethod

from tycherion.domain.portfolio.entities import SignalsBySymbol, TargetAllocation


class BaseAllocator(ABC):
    """Abstract base class for portfolio allocator plugins."""

    # Set by decorator
    name: str = ""
    tags: set[str] = set()

    @abstractmethod
    def allocate(self, signals: SignalsBySymbol) -> TargetAllocation:
        raise NotImplementedError
