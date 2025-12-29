from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Mapping

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetrySink


def _short(v: Any, limit: int = 80) -> str:
    s = str(v)
    return s if len(s) <= limit else (s[: limit - 1] + "…")


def _summarize(event: TelemetryEvent) -> str:
    scope = dict(event.scope or {})
    payload = dict(event.payload or {})

    # Prefer common identifiers
    parts: list[str] = []
    for k in ("stage", "symbol", "model"):
        if k in scope and scope[k] not in (None, ""):
            parts.append(f"{k}={_short(scope[k], 40)}")

    # Add a small, curated payload summary
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
        if k in payload:
            parts.append(f"{k}={_short(payload[k], 40)}")

    # If nothing matched, expose payload keys (but not full payload)
    if not parts and payload:
        parts.append(f"payload_keys={list(payload.keys())[:8]}")

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
        msg = (
            f"[{event.level.value}]"
            f"[{event.channel}]"
            f"[{event.run_id}] "
            f"{event.name}"
        )
        summary = _summarize(event)
        if summary:
            msg = f"{msg} {summary}"
        try:
            self.stream.write(msg + "\n")
            self.stream.flush()
        except Exception:
            return
