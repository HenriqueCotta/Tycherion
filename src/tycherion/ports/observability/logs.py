from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import Attributes, Severity


@runtime_checkable
class LoggerPort(Protocol):
    def emit(self, body: str, severity: Severity, attributes: Attributes | None = None) -> None: ...
    def is_enabled(self, severity: Severity) -> bool: ...


@runtime_checkable
class LoggerProviderPort(Protocol):
    def get_logger(self, name: str, version: str | None = None) -> LoggerPort: ...
