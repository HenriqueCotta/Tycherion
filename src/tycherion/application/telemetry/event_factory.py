from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_event(
    *,
    trace_id: str,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    name: str,
    level: str | TelemetryLevel,
    channel: str,
    attributes: Mapping[str, Any] | None = None,
    data: Mapping[str, Any] | None = None,
    schema_version: int = 2,
) -> TelemetryEvent:
    return TelemetryEvent(
        ts_utc=now_utc(),
        trace_id=str(trace_id),
        span_id=(str(span_id) if span_id is not None else None),
        parent_span_id=(str(parent_span_id) if parent_span_id is not None else None),
        name=str(name),
        level=TelemetryLevel.coerce(level),
        channel=str(channel),
        attributes=(dict(attributes or {}) if attributes is not None else None),
        data=dict(data or {}),
        schema_version=int(schema_version),
    )
