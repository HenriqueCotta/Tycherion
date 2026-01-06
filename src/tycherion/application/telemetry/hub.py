from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetryPort, TelemetrySink


@dataclass(slots=True)
class TelemetryHub(TelemetryPort):
    """Fan-out hub.

    The hub is application-layer infrastructure: it receives canonical
    TelemetryEvent envelopes and forwards them to sinks. Sinks can filter
    independently.
    """

    sinks: list[TelemetrySink]
    base_attributes: Mapping[str, Any] | None = None

    def emit(self, event: TelemetryEvent) -> None:
        attributes = dict(self.base_attributes or {})
        if event.attributes:
            attributes.update(dict(event.attributes))
        merged = TelemetryEvent(
            schema_version=event.schema_version,
            runner_id=event.runner_id,
            trace_id=event.trace_id,
            event_seq=event.event_seq,
            ts_utc=event.ts_utc,
            mono_ns=event.mono_ns,
            span_id=event.span_id,
            parent_span_id=event.parent_span_id,
            name=event.name,
            level=event.level,
            channel=event.channel,
            attributes=attributes if attributes else None,
            data=dict(event.data or {}),
        )

        for s in list(self.sinks):
            try:
                if not s.enabled(merged.channel, merged.level, merged.name):
                    continue
                s.emit(merged)
            except Exception:
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

    def child(self, attributes: Mapping[str, Any]) -> TelemetryPort:
        merged = dict(self.base_attributes or {})
        merged.update(dict(attributes or {}))
        return TelemetryHub(sinks=self.sinks, base_attributes=merged)

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
