from __future__ import annotations

import hashlib
import json
import time
import threading
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Mapping

from tycherion.application.telemetry.event_factory import make_event, now_utc
from tycherion.application.telemetry.ids import make_span_id
from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetryPort

# Bump when TelemetryEvent fields change in a backwards-incompatible way.
SCHEMA_VERSION = 3

# Per-task span stack (works for sync, async, nested contexts)
_SPAN_STACK: ContextVar[tuple[str, ...]] = ContextVar("tycherion_span_stack", default=())


def stable_config_hash(
    cfg_dump: Mapping[str, Any],
    *,
    redactions: Mapping[str, set[str]] | None = None,
) -> str:
    """Best-effort hash of a config dump, with sensitive fields redacted.

    `cfg_dump` is expected to be the output of pydantic's `model_dump()`.
    """

    redactions = redactions or {"mt5": {"password", "login", "server"}}

    payload = json.loads(json.dumps(cfg_dump, default=str))  # ensure JSON-ish types
    for section, keys in redactions.items():
        node = payload.get(section)
        if isinstance(node, dict):
            for k in keys:
                if k in node:
                    node[k] = "***"

    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class _TraceState:
    """Mutable, shared state for one trace (shared across child tracers)."""

    __slots__ = ("span_seq", "event_seq", "_lock")

    def __init__(self) -> None:
        self.span_seq = 0
        self.event_seq = 0
        self._lock = threading.Lock()

    def next_span_id(self) -> str:
        with self._lock:
            self.span_seq += 1
            return make_span_id(self.span_seq)

    def next_event_seq(self) -> int:
        with self._lock:
            self.event_seq += 1
            return int(self.event_seq)


@dataclass(frozen=True, slots=True)
class TraceTelemetry:
    """A lightweight tracer aligned with standard observability vocabulary.

    This is intentionally NOT OpenTelemetry SDK. It's a small abstraction that
    keeps the mental model: runner_id + trace_id + spans + structured events.
    """

    port: TelemetryPort | None
    runner_id: str
    trace_id: str
    base_attributes: Mapping[str, Any] | None = None
    _state: Any | None = None

    def __post_init__(self) -> None:
        # dataclass(frozen=True): use object.__setattr__
        if self._state is None:
            object.__setattr__(self, "_state", _TraceState())

    def enabled(self, channel: str, level: str | TelemetryLevel) -> bool:
        try:
            return bool(self.port and self.port.enabled(channel, level))
        except Exception:
            return False

    def child(self, attributes: Mapping[str, Any]) -> "TraceTelemetry":
        merged = dict(self.base_attributes or {})
        merged.update(dict(attributes or {}))
        return TraceTelemetry(
            port=self.port,
            runner_id=self.runner_id,
            trace_id=self.trace_id,
            base_attributes=merged,
            _state=self._state,
        )

    def _emit_built(self, ev: TelemetryEvent) -> None:
        if not self.port:
            return
        try:
            self.port.emit(ev)
        except Exception:
            return

    def emit(
        self,
        *,
        name: str,
        level: str | TelemetryLevel,
        channel: str,
        attributes: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        span_id: str | None = None,
        parent_span_id: str | None = None,
        mono_ns: int | None = None,
        ts_utc: Any | None = None,
    ) -> None:
        if not self.port:
            return

        lvl = TelemetryLevel.coerce(level)
        # Gating first: do not even increment event_seq if nobody is listening.
        try:
            if not self.port.enabled(channel, lvl):
                return
        except Exception:
            return

        try:
            event_seq = self._state.next_event_seq()  # type: ignore[union-attr]
            base = dict(self.base_attributes or {})
            if attributes:
                base.update(dict(attributes))

            stack = _SPAN_STACK.get()
            resolved_span_id = span_id if span_id is not None else (stack[-1] if stack else None)
            resolved_parent_span_id = (
                parent_span_id
                if parent_span_id is not None
                else (stack[-2] if len(stack) >= 2 else None)
            )

            ev = make_event(
                schema_version=SCHEMA_VERSION,
                runner_id=self.runner_id,
                trace_id=self.trace_id,
                event_seq=event_seq,
                ts_utc=(ts_utc or now_utc()),
                mono_ns=mono_ns,
                span_id=resolved_span_id,
                parent_span_id=resolved_parent_span_id,
                name=name,
                level=lvl,
                channel=channel,
                attributes=base if base else None,
                data=data or {},
            )
            self._emit_built(ev)
        except Exception:
            return

    def span(
        self,
        name: str,
        *,
        channel: str = "ops",
        level: str | TelemetryLevel = TelemetryLevel.INFO,
        attributes: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
    ) -> "Span":
        return Span(
            tracer=self,
            name=str(name),
            channel=str(channel),
            level=TelemetryLevel.coerce(level),
            attributes=dict(attributes or {}) if attributes else None,
            data=dict(data or {}) if data else None,
        )


@dataclass(slots=True)
class Span:
    tracer: TraceTelemetry
    name: str
    channel: str
    level: TelemetryLevel
    attributes: Mapping[str, Any] | None
    data: Mapping[str, Any] | None

    span_id: str | None = None
    parent_span_id: str | None = None
    _token: Any | None = None
    _t0_mono: int | None = None

    def __enter__(self) -> "Span":
        self._t0_mono = time.monotonic_ns()

        before = _SPAN_STACK.get()
        self.parent_span_id = before[-1] if before else None
        self.span_id = self.tracer._state.next_span_id()  # type: ignore[union-attr]

        self._token = _SPAN_STACK.set(before + (self.span_id,))

        self.tracer.emit(
            name=f"{self.name}.started",
            level=self.level,
            channel=self.channel,
            attributes=self.attributes,
            data=self.data,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            mono_ns=self._t0_mono,
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            t1 = time.monotonic_ns()
            duration_ms = int(round((t1 - int(self._t0_mono or t1)) / 1_000_000))

            if exc is None:
                self.tracer.emit(
                    name=f"{self.name}.finished",
                    level=TelemetryLevel.INFO,
                    channel=self.channel,
                    attributes=self.attributes,
                    data={"duration_ms": duration_ms, "status": "ok"},
                    span_id=self.span_id,
                    parent_span_id=self.parent_span_id,
                    mono_ns=t1,
                )
                return False

            self.tracer.emit(
                name=f"{self.name}.failed",
                level=TelemetryLevel.ERROR,
                channel=self.channel,
                attributes=self.attributes,
                data={
                    "duration_ms": duration_ms,
                    "status": "error",
                    "exception_type": getattr(exc_type, "__name__", str(exc_type)),
                    "message": str(exc),
                },
                span_id=self.span_id,
                parent_span_id=self.parent_span_id,
                mono_ns=t1,
            )
            return False
        finally:
            try:
                if self._token is not None:
                    _SPAN_STACK.reset(self._token)
            except Exception:
                pass
