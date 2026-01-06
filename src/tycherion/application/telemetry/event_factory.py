from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_event(
    *,
    schema_version: int,
    runner_id: str,
    trace_id: str,
    event_seq: int,
    ts_utc: datetime | None = None,
    mono_ns: int | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    name: str,
    level: str | TelemetryLevel,
    channel: str,
    attributes: Mapping[str, Any] | None = None,
    data: Mapping[str, Any] | None = None,
) -> TelemetryEvent:
    return TelemetryEvent(
        schema_version=int(schema_version),
        runner_id=str(runner_id),
        trace_id=str(trace_id),
        event_seq=int(event_seq),
        ts_utc=(ts_utc or now_utc()),
        mono_ns=(int(mono_ns) if mono_ns is not None else None),
        span_id=(str(span_id) if span_id is not None else None),
        parent_span_id=(str(parent_span_id) if parent_span_id is not None else None),
        name=str(name),
        level=TelemetryLevel.coerce(level),
        channel=str(channel),
        attributes=(dict(attributes or {}) if attributes is not None else None),
        data=dict(data or {}),
    )
