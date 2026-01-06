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

    Design goals:
    - stable schema (versioned)
    - append-only journaling friendly
    - deterministic ordering within a trace (event_seq)

    NOTE: `attributes` and `data` must be JSON-serialisable.
    """

    schema_version: int
    runner_id: str
    trace_id: str

    # Order within the trace (1..N). Useful for ordering + idempotent dedupe in sinks.
    event_seq: int

    # When the event happened (audit / timeline)
    ts_utc: datetime

    # Optional monotonic timestamp for precision timing (not affected by NTP).
    mono_ns: int | None

    # Hierarchy
    span_id: str | None
    parent_span_id: str | None

    # Semantic payload
    name: str
    level: TelemetryLevel
    channel: str
    attributes: Mapping[str, Any] | None
    data: Mapping[str, Any]


class TelemetrySink(Protocol):
    """Adapter-side sink.

    A sink can filter independently. The hub will call `enabled` for gating,
    then `emit` to persist/print.
    """

    def enabled(self, channel: str, level: TelemetryLevel, name: str | None = None) -> bool: ...

    def emit(self, event: TelemetryEvent) -> None: ...


class TelemetryPort(Protocol):
    """Application-facing telemetry API (fan-out hub + scoped wrappers)."""

    def emit(self, event: TelemetryEvent) -> None: ...

    def enabled(self, channel: str, level: str | TelemetryLevel) -> bool: ...

    def child(self, attributes: Mapping[str, Any]) -> "TelemetryPort": ...

    def flush(self) -> None: ...

    def close(self) -> None: ...
