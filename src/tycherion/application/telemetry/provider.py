from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Mapping

from tycherion.application.telemetry.event_factory import now_utc
from tycherion.application.telemetry.ids import make_trace_id, sanitize_runner_id
from tycherion.application.telemetry.trace import TraceTelemetry
from tycherion.ports.telemetry import TelemetryPort


@dataclass(slots=True)
class TelemetryProvider:
    """Factory for per-run TraceTelemetry objects.

    Centralising trace creation prevents each runmode from inventing its own trace_id
    and keeps ID format consistent across the system.
    """

    runner_id: str
    hub: TelemetryPort
    _trace_counter: Any = None

    def __post_init__(self) -> None:
        self.runner_id = sanitize_runner_id(self.runner_id)
        # start at 0, so the first next() is 1
        self._trace_counter = itertools.count(1)

    def new_trace(self, base_attributes: Mapping[str, Any] | None = None) -> TraceTelemetry:
        ts = now_utc()
        seq = int(next(self._trace_counter))
        trace_id = make_trace_id(self.runner_id, ts, seq)
        return TraceTelemetry(
            port=self.hub,
            runner_id=self.runner_id,
            trace_id=trace_id,
            base_attributes=(dict(base_attributes or {}) if base_attributes else None),
        )

    def flush(self) -> None:
        try:
            self.hub.flush()
        except Exception:
            return

    def close(self) -> None:
        try:
            self.hub.close()
        except Exception:
            return
