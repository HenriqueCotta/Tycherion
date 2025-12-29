from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetrySink


@dataclass(slots=True)
class InMemoryTelemetrySink(TelemetrySink):
    """Test-friendly telemetry sink.

    Stores events in memory so tests can assert on them without stdout/DB.
    """

    enabled_flag: bool = True
    channels: set[str] = field(default_factory=lambda: {"audit", "ops"})
    min_level: TelemetryLevel = TelemetryLevel.INFO
    events: list[TelemetryEvent] = field(default_factory=list)

    def enabled(self, channel: str, level: TelemetryLevel, name: str | None = None) -> bool:
        _ = name
        if not self.enabled_flag:
            return False
        if channel not in self.channels:
            return False
        return TelemetryLevel.coerce(level).rank() >= TelemetryLevel.coerce(self.min_level).rank()

    def emit(self, event: TelemetryEvent) -> None:
        self.events.append(event)
