from __future__ import annotations

import hashlib
import json
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Mapping

from tycherion.application.telemetry.event_factory import make_event
from tycherion.ports.telemetry import TelemetryLevel, TelemetryPort


_SPAN_STACK: ContextVar[tuple[str, ...]] = ContextVar("tycherion_span_stack", default=())


def new_trace_id() -> str:
    """32 hex chars, stable to store/search."""

    return uuid.uuid4().hex


def new_span_id() -> str:
    """16 hex chars (shorter, still plenty for a run-local tree)."""

    return uuid.uuid4().hex[:16]


def stable_config_hash(
    cfg_dump: Mapping[str, Any],
    *,
    redactions: Mapping[str, set[str]] | None = None,
) -> str:
    """Best-effort hash of a config dump, with sensitive fields redacted.

    `cfg_dump` is expected to be the output of pydantic's `model_dump()`.
    """

    # Default redactions (kept narrow and explicit).
    redactions = redactions or {"mt5": {"password", "login", "server"}}

    payload = json.loads(json.dumps(cfg_dump, default=str))  # ensure plain JSON-ish types
    for section, keys in redactions.items():
        node = payload.get(section)
        if isinstance(node, dict):
            for k in keys:
                if k in node:
                    node[k] = "***"

    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TraceTelemetry:
    """A lightweight tracer aligned with standard observability vocabulary.

    This is intentionally NOT OpenTelemetry SDK. It's a small abstraction that
    lets Tycherion keep the mental model: trace_id + spans + structured data.
    """

    port: TelemetryPort | None
    trace_id: str
    base_attributes: Mapping[str, Any] | None = None

    def enabled(self, channel: str, level: str | TelemetryLevel) -> bool:
        try:
            return bool(self.port and self.port.enabled(channel, level))
        except Exception:
            return False

    def child(self, attributes: Mapping[str, Any]) -> "TraceTelemetry":
        merged = dict(self.base_attributes or {})
        merged.update(dict(attributes or {}))
        return TraceTelemetry(port=self.port, trace_id=self.trace_id, base_attributes=merged)

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
    ) -> None:
        if not self.port:
            return
        try:
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
                trace_id=self.trace_id,
                span_id=resolved_span_id,
                parent_span_id=resolved_parent_span_id,
                name=name,
                level=level,
                channel=channel,
                attributes=base if base else None,
                data=data or {},
                schema_version=2,
            )
            self.port.emit(ev)
        except Exception:
            # telemetry must never break the run
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
    _t0: float | None = None

    def __enter__(self) -> "Span":
        self._t0 = time.perf_counter()

        before = _SPAN_STACK.get()
        self.parent_span_id = before[-1] if before else None
        self.span_id = new_span_id()

        self._token = _SPAN_STACK.set(before + (self.span_id,))

        self.tracer.emit(
            name=f"{self.name}.started",
            level=self.level,
            channel=self.channel,
            attributes=self.attributes,
            data=self.data,
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            t1 = time.perf_counter()
            duration_ms = int(round((t1 - float(self._t0 or t1)) * 1000))

            if exc is None:
                self.tracer.emit(
                    name=f"{self.name}.finished",
                    level=TelemetryLevel.INFO,
                    channel=self.channel,
                    attributes=self.attributes,
                    data={"duration_ms": duration_ms, "status": "ok"},
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
            )
            return False
        finally:
            try:
                if self._token is not None:
                    _SPAN_STACK.reset(self._token)
            except Exception:
                # best-effort: avoid masking original exceptions
                pass
