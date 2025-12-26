from __future__ import annotations

from abc import ABC, abstractmethod

from tycherion.domain.portfolio.entities import (
    PortfolioSnapshot,
    TargetAllocation,
    RebalanceInstruction,
)


class BaseBalancer(ABC):
    """Abstract base class for portfolio balancer / rebalancer plugins."""

    # Set by decorator
    name: str = ""
    tags: set[str] = set()

    @abstractmethod
    def plan(
        self,
        portfolio: PortfolioSnapshot,
        target: TargetAllocation,
        threshold: float = 0.25,
    ) -> list[RebalanceInstruction]:
        raise NotImplementedError
