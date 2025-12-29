from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetryPort, TelemetrySink


@dataclass(slots=True)
class TelemetryHub(TelemetryPort):
    """Fan-out hub.

    The hub is application-layer infrastructure: it receives canonical
    TelemetryEvent envelopes and forwards them to sinks. Sinks can filter
    independently.
    """

    sinks: list[TelemetrySink]
    base_scope: Mapping[str, Any] | None = None

    def emit(self, event: TelemetryEvent) -> None:
        scope = dict(self.base_scope or {})
        if event.scope:
            scope.update(dict(event.scope))
        merged = TelemetryEvent(
            ts_utc=event.ts_utc,
            run_id=event.run_id,
            name=event.name,
            level=event.level,
            channel=event.channel,
            scope=scope,
            payload=dict(event.payload or {}),
            schema_version=event.schema_version,
        )

        for s in list(self.sinks):
            try:
                if not s.enabled(merged.channel, merged.level, merged.name):
                    continue
                s.emit(merged)
            except Exception:
                # telemetry must never break the run
                continue

    def enabled(self, channel: str, level: str | TelemetryLevel) -> bool:
        lv = TelemetryLevel.coerce(level)
        for s in list(self.sinks):
            try:
                if s.enabled(str(channel), lv, None):
                    return True
            except Exception:
                continue
        return False

    def child(self, scope: Mapping[str, Any]) -> TelemetryPort:
        merged = dict(self.base_scope or {})
        merged.update(dict(scope or {}))
        return TelemetryHub(sinks=self.sinks, base_scope=merged)

    def flush(self) -> None:
        for s in list(self.sinks):
            flush = getattr(s, "flush", None)
            if callable(flush):
                try:
                    flush()
                except Exception:
                    continue

    def close(self) -> None:
        for s in list(self.sinks):
            close = getattr(s, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    continue
