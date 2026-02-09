from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import Attributes


@runtime_checkable
class CounterPort(Protocol):
    def add(self, amount: int, attributes: Attributes | None = None) -> None: ...


@runtime_checkable
class MeterPort(Protocol):
    def create_counter(self, name: str, unit: str | None = None, description: str | None = None) -> CounterPort: ...


@runtime_checkable
class MeterProviderPort(Protocol):
    def get_meter(self, name: str, version: str | None = None) -> MeterPort: ...
