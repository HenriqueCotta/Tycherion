from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace as otel_trace  # type: ignore
from opentelemetry.trace.status import Status, StatusCode  # type: ignore

from tycherion.adapters.observability.otel.console_dev import ConsoleRenderer
from tycherion.ports.observability import semconv
from tycherion.ports.observability.traces import SpanPort, TracerPort, TracerProviderPort
from tycherion.ports.observability.types import Attributes


def _hex_trace_id(span_or_ctx: Any) -> str | None:
    try:
        ctx = span_or_ctx.get_span_context()
        if not getattr(ctx, "is_valid", False):
            return None
        return format(int(ctx.trace_id), "032x")
    except Exception:
        return None


def _hex_span_id(span_or_ctx: Any) -> str | None:
    try:
        ctx = span_or_ctx.get_span_context()
        if not getattr(ctx, "is_valid", False):
            return None
        return format(int(ctx.span_id), "016x")
    except Exception:
        return None


class OtelSpan(SpanPort):
    def __init__(
        self,
        span: Any,
        *,
        schema_version: str,
        console: ConsoleRenderer,
    ) -> None:
        self._span = span
        self._schema_version = schema_version
        self._console = console

        self._trace_id_hex = _hex_trace_id(span) or None
        self._span_id_hex = _hex_span_id(span) or None
        self._start_ns = time.time_ns()
        self._status = "UNSET"

    @property
    def trace_id_hex(self) -> str | None:
        return self._trace_id_hex

    @property
    def span_id_hex(self) -> str | None:
        return self._span_id_hex

    @property
    def status(self) -> str:
        return self._status

    @property
    def start_ns(self) -> int:
        return self._start_ns

    def set_attribute(self, key: str, value: object) -> None:
        try:
            self._span.set_attribute(key, value)
        except Exception:
            return None

    def set_attributes(self, attributes: Attributes) -> None:
        for k, v in (attributes or {}).items():
            self.set_attribute(k, v)

    def _decorate_event_attrs(self, attributes: Attributes | None) -> dict[str, Any]:
        attrs: dict[str, Any] = dict(attributes or {})
        attrs[semconv.TYCHERION_SCHEMA_VERSION] = self._schema_version
        return attrs

    def add_event(self, name: str, attributes: Attributes | None = None) -> None:
        attrs = self._decorate_event_attrs(attributes)

        try:
            self._span.add_event(name, attributes=attrs)
        except Exception:
            pass

        self._console.span_event(
            name=name,
            attributes=attrs,
            trace_id=self._trace_id_hex,
            span_id=self._span_id_hex,
        )

    def record_exception(self, exc: BaseException) -> None:
        try:
            self._span.record_exception(exc)
        except Exception:
            return None

    def set_status_ok(self) -> None:
        self._status = "OK"
        try:
            self._span.set_status(Status(StatusCode.OK))
        except Exception:
            return None

    def set_status_error(self, message: str | None = None) -> None:
        self._status = "ERROR"
        try:
            self._span.set_status(Status(StatusCode.ERROR, description=message))
        except Exception:
            return None

    def is_recording(self) -> bool:
        try:
            return bool(self._span.is_recording())
        except Exception:
            return False


class OtelTracer(TracerPort):
    def __init__(
        self,
        tracer: Any,
        *,
        schema_version: str,
        console: ConsoleRenderer,
    ) -> None:
        self._tracer = tracer
        self._schema_version = schema_version
        self._console = console

    def _decorate_span_attrs(self, attributes: Attributes | None) -> dict[str, Any]:
        attrs: dict[str, Any] = dict(attributes or {})
        attrs.setdefault(semconv.TYCHERION_SCHEMA_VERSION, self._schema_version)
        return attrs

    @contextmanager
    def start_as_current_span(self, name: str, attributes: Attributes | None = None):
        attrs = self._decorate_span_attrs(attributes)

        start_ns = time.time_ns()
        with self._tracer.start_as_current_span(name, attributes=attrs) as span:
            trace_id_hex = _hex_trace_id(span) or ""
            span_id_hex = _hex_span_id(span) or ""

            wrapped = OtelSpan(
                span,
                schema_version=self._schema_version,
                console=self._console,
            )
            self._console.span_started(
                name=name,
                attributes=attrs,
                trace_id=trace_id_hex,
                span_id=span_id_hex,
            )
            try:
                yield wrapped
            finally:
                end_ns = time.time_ns()
                duration_ms = (end_ns - start_ns) / 1_000_000
                error = wrapped.status == "ERROR"
                self._console.span_ended(
                    name=name,
                    status=wrapped.status,
                    duration_ms=duration_ms,
                    trace_id=trace_id_hex,
                    span_id=span_id_hex,
                    error=error,
                )


class OtelTracerProvider(TracerProviderPort):
    def __init__(
        self,
        provider: Any,
        *,
        schema_version: str,
        console: ConsoleRenderer,
    ) -> None:
        self._provider = provider
        self._schema_version = schema_version
        self._console = console

    def get_tracer(self, name: str, version: str | None = None) -> TracerPort:
        tracer = self._provider.get_tracer(name, version)
        return OtelTracer(
            tracer,
            schema_version=self._schema_version,
            console=self._console,
        )
