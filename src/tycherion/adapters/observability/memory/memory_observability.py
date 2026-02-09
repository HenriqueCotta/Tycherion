from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
import secrets
import time
from typing import Any, Dict, List, Optional

import contextvars

from tycherion.ports.observability.logs import LoggerPort, LoggerProviderPort
from tycherion.ports.observability.metrics import CounterPort, MeterPort, MeterProviderPort
from tycherion.ports.observability.observability import ObservabilityPort
from tycherion.ports.observability.traces import SpanPort, TracerPort, TracerProviderPort
from tycherion.ports.observability.types import Attributes, Severity, TYCHERION_SCHEMA_VERSION


_current_span: contextvars.ContextVar["MemorySpan | None"] = contextvars.ContextVar("tycherion_mem_current_span", default=None)
_current_trace_state: contextvars.ContextVar["_TraceState | None"] = contextvars.ContextVar("tycherion_mem_trace_state", default=None)


@dataclass
class _TraceState:
    trace_id: str
    event_seq: int = 0


def _new_trace_id() -> str:
    return secrets.token_hex(16)  # 32 hex chars


def _new_span_id() -> str:
    return secrets.token_hex(8)  # 16 hex chars


@dataclass
class MemorySpan(SpanPort):
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    start_ns: int = field(default_factory=time.time_ns)
    end_ns: Optional[int] = None
    status: str = "UNSET"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def set_attributes(self, attributes: Attributes) -> None:
        for k, v in attributes.items():
            self.attributes[k] = v

    def add_event(self, name: str, attributes: Attributes | None = None) -> None:
        st = _current_trace_state.get()
        seq = None
        if st and st.trace_id == self.trace_id:
            st.event_seq += 1
            seq = st.event_seq

        ev_attrs: Dict[str, Any] = dict(attributes or {})
        ev_attrs["tycherion.schema_version"] = TYCHERION_SCHEMA_VERSION
        if seq is not None:
            ev_attrs["tycherion.event_seq"] = seq

        self.events.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "name": name,
                "attributes": ev_attrs,
            }
        )

    def record_exception(self, exc: BaseException) -> None:
        self.exceptions.append(repr(exc))

    def set_status_ok(self) -> None:
        self.status = "OK"

    def set_status_error(self, message: str | None = None) -> None:
        self.status = "ERROR"
        if message:
            self.attributes.setdefault("error.message", message)

    def is_recording(self) -> bool:
        return True


class MemoryTracer(TracerPort):
    def __init__(self, sink: "MemorySink") -> None:
        self._sink = sink

    @contextmanager
    def start_as_current_span(self, name: str, attributes: Attributes | None = None):
        parent = _current_span.get()
        if parent is None:
            trace_id = _new_trace_id()
            _current_trace_state.set(_TraceState(trace_id=trace_id, event_seq=0))
        else:
            trace_id = parent.trace_id

        span = MemorySpan(
            name=name,
            trace_id=trace_id,
            span_id=_new_span_id(),
            parent_span_id=parent.span_id if parent else None,
        )
        span.set_attributes(attributes or {})
        token = _current_span.set(span)
        self._sink.spans_started.append(span)
        try:
            yield span
        finally:
            span.end_ns = time.time_ns()
            _current_span.reset(token)
            self._sink.spans_ended.append(span)
            if parent is None:
                _current_trace_state.set(None)


class MemoryTracerProvider(TracerProviderPort):
    def __init__(self, sink: "MemorySink") -> None:
        self._sink = sink

    def get_tracer(self, name: str, version: str | None = None) -> TracerPort:
        return MemoryTracer(self._sink)


@dataclass
class MemoryLogRecord:
    ts: str
    body: str
    severity: Severity
    attributes: Dict[str, Any]
    trace_id: Optional[str]
    span_id: Optional[str]


class MemoryLogger(LoggerPort):
    def __init__(self, sink: "MemorySink", min_severity: Severity = Severity.INFO) -> None:
        self._sink = sink
        self._min_severity = min_severity
        self._rank = {
            Severity.TRACE: 0,
            Severity.DEBUG: 10,
            Severity.INFO: 20,
            Severity.WARN: 30,
            Severity.ERROR: 40,
            Severity.FATAL: 50,
        }

    def is_enabled(self, severity: Severity) -> bool:
        return self._rank[severity] >= self._rank[self._min_severity]

    def emit(self, body: str, severity: Severity, attributes: Attributes | None = None) -> None:
        if not self.is_enabled(severity):
            return

        span = _current_span.get()
        trace_id = span.trace_id if span else None
        span_id = span.span_id if span else None

        st = _current_trace_state.get()
        seq = None
        if st and trace_id and st.trace_id == trace_id:
            st.event_seq += 1
            seq = st.event_seq

        attrs: Dict[str, Any] = dict(attributes or {})
        attrs["tycherion.schema_version"] = TYCHERION_SCHEMA_VERSION
        if seq is not None:
            attrs["tycherion.event_seq"] = seq

        self._sink.logs.append(
            MemoryLogRecord(
                ts=datetime.now(timezone.utc).isoformat(),
                body=body,
                severity=severity,
                attributes=attrs,
                trace_id=trace_id,
                span_id=span_id,
            )
        )


class MemoryLoggerProvider(LoggerProviderPort):
    def __init__(self, sink: "MemorySink", min_severity: Severity = Severity.INFO) -> None:
        self._sink = sink
        self._min_severity = min_severity

    def get_logger(self, name: str, version: str | None = None) -> LoggerPort:
        return MemoryLogger(self._sink, min_severity=self._min_severity)


class MemoryCounter(CounterPort):
    def add(self, amount: int, attributes: Attributes | None = None) -> None:
        return None


class MemoryMeter(MeterPort):
    def create_counter(self, name: str, unit: str | None = None, description: str | None = None) -> CounterPort:
        return MemoryCounter()


class MemoryMeterProvider(MeterProviderPort):
    def get_meter(self, name: str, version: str | None = None) -> MeterPort:
        return MemoryMeter()


@dataclass
class MemorySink:
    spans_started: List[MemorySpan] = field(default_factory=list)
    spans_ended: List[MemorySpan] = field(default_factory=list)
    logs: List[MemoryLogRecord] = field(default_factory=list)


class MemoryObservability(ObservabilityPort):
    def __init__(self, min_log_severity: Severity = Severity.INFO) -> None:
        self.sink = MemorySink()
        self._traces = MemoryTracerProvider(self.sink)
        self._logs = MemoryLoggerProvider(self.sink, min_severity=min_log_severity)
        self._metrics = MemoryMeterProvider()

    @property
    def traces(self) -> TracerProviderPort:
        return self._traces

    @property
    def logs(self) -> LoggerProviderPort:
        return self._logs

    @property
    def metrics(self) -> MeterProviderPort:
        return self._metrics

    def shutdown(self) -> None:
        return None

    def force_flush(self) -> None:
        return None
