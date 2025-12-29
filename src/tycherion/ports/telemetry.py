from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Protocol


class TelemetryLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"

    @classmethod
    def coerce(cls, value: str | "TelemetryLevel") -> "TelemetryLevel":
        if isinstance(value, TelemetryLevel):
            return value
        v = (value or "INFO").upper().strip()
        try:
            return TelemetryLevel(v)
        except Exception:
            return TelemetryLevel.INFO

    def rank(self) -> int:
        order = {
            TelemetryLevel.DEBUG: 10,
            TelemetryLevel.INFO: 20,
            TelemetryLevel.WARN: 30,
            TelemetryLevel.ERROR: 40,
        }
        return int(order[self])


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    """Canonical, small telemetry envelope.

    NOTE: `scope` and `payload` must be JSON-serialisable.
    """

    ts_utc: datetime
    run_id: str
    name: str
    level: TelemetryLevel
    channel: str
    scope: Mapping[str, Any] | None
    payload: Mapping[str, Any]
    schema_version: int = 1


class TelemetrySink(Protocol):
    """Adapter-side sink.

    A sink can filter independently. The hub will call `enabled` to determine
    whether some payload should be built (gating), then `emit` to persist/print.
    """

    def enabled(self, channel: str, level: TelemetryLevel, name: str | None = None) -> bool: ...

    def emit(self, event: TelemetryEvent) -> None: ...


class TelemetryPort(Protocol):
    """Application-facing telemetry API (fan-out hub + scoped wrappers)."""

    def emit(self, event: TelemetryEvent) -> None: ...

    def enabled(self, channel: str, level: str | TelemetryLevel) -> bool: ...

    def child(self, scope: Mapping[str, Any]) -> "TelemetryPort": ...
