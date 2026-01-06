from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetrySink


def _short(v: Any, limit: int = 80) -> str:
    s = str(v)
    return s if len(s) <= limit else (s[: limit - 1] + "…")


def _summarize(event: TelemetryEvent) -> str:
    attributes = dict(event.attributes or {})
    data = dict(event.data or {})

    parts: list[str] = []
    for k in ("component", "stage", "symbol", "model"):
        if k in attributes and attributes[k] not in (None, ""):
            parts.append(f"{k}={_short(attributes[k], 40)}")

    for k in (
        "dropped_count",
        "passed_count",
        "symbols_count",
        "duration_ms",
        "threshold",
        "score",
        "side",
        "weight",
        "confidence",
        "reason",
    ):
        if k in data:
            parts.append(f"{k}={_short(data[k], 40)}")

    if not parts and data:
        parts.append(f"data_keys={list(data.keys())[:8]}")

    return " ".join(parts)


@dataclass(slots=True)
class ConsoleTelemetrySink(TelemetrySink):
    """Human-friendly console output.

    Default should be disabled via config. When enabled, prints one line per event.
    """

    enabled_flag: bool = False
    channels: set[str] = field(default_factory=lambda: {"ops"})
    min_level: TelemetryLevel = TelemetryLevel.INFO
    stream: Any = sys.stdout

    def enabled(self, channel: str, level: TelemetryLevel, name: str | None = None) -> bool:
        _ = name
        if not self.enabled_flag:
            return False
        if channel not in self.channels:
            return False
        return TelemetryLevel.coerce(level).rank() >= TelemetryLevel.coerce(self.min_level).rank()

    def emit(self, event: TelemetryEvent) -> None:
        # Keep this stable and easy to grep
        trace_short = _short(event.trace_id, 18)
        msg = (
            f"[{event.level.value}]"
            f"[{event.channel}]"
            f"[runner={_short(event.runner_id, 18)}]"
            f"[trace={trace_short}]"
            f"[event_seq={event.event_seq}]"
        )

        if event.span_id:
            msg += f"[span={_short(event.span_id, 8)}]"
        if event.parent_span_id:
            msg += f"[parent={_short(event.parent_span_id, 8)}]"

        msg += f" {event.name}"
        summary = _summarize(event)
        if summary:
            msg = f"{msg} {summary}"
        try:
            self.stream.write(msg + "\n")
            self.stream.flush()
        except Exception:
            return
