from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_event(
    *,
    run_id: str,
    name: str,
    level: str | TelemetryLevel,
    channel: str,
    scope: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    schema_version: int = 1,
) -> TelemetryEvent:
    return TelemetryEvent(
        ts_utc=now_utc(),
        run_id=str(run_id),
        name=str(name),
        level=TelemetryLevel.coerce(level),
        channel=str(channel),
        scope=dict(scope or {}),
        payload=dict(payload or {}),
        schema_version=int(schema_version),
    )
