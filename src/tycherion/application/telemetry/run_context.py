from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from tycherion.application.telemetry.event_factory import make_event
from tycherion.ports.telemetry import TelemetryLevel, TelemetryPort


@dataclass(frozen=True, slots=True)
class RunContext:
    run_id: str
    timeframe: str
    lookback_days: int
    started_utc: datetime
    config_hash: str | None = None


@dataclass(slots=True)
class RunTelemetry:
    """Ergonomic wrapper to produce consistent events for a single run_id."""

    port: TelemetryPort | None
    run_id: str
    base_scope: Mapping[str, Any] | None = None

    def enabled(self, channel: str, level: str | TelemetryLevel) -> bool:
        if self.port is None:
            return False
        return self.port.enabled(channel, level)

    def emit(
        self,
        *,
        name: str,
        channel: str,
        level: str | TelemetryLevel = TelemetryLevel.INFO,
        scope: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
        schema_version: int = 1,
    ) -> None:
        if self.port is None:
            return

        merged_scope = dict(self.base_scope or {})
        if scope:
            merged_scope.update(dict(scope))

        try:
            self.port.emit(
                make_event(
                    run_id=self.run_id,
                    name=name,
                    level=level,
                    channel=channel,
                    scope=merged_scope,
                    payload=payload,
                    schema_version=schema_version,
                )
            )
        except Exception:
            # never break the run due to telemetry
            return

    def child(self, scope: Mapping[str, Any]) -> "RunTelemetry":
        merged = dict(self.base_scope or {})
        merged.update(dict(scope or {}))
        return RunTelemetry(port=self.port, run_id=self.run_id, base_scope=merged)
