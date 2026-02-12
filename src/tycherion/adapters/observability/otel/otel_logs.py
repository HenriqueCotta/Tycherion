from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace as otel_trace  # type: ignore

from tycherion.adapters.observability.otel.console_dev import ConsoleRenderer
from tycherion.ports.observability import semconv
from tycherion.ports.observability.logs import LoggerPort, LoggerProviderPort
from tycherion.ports.observability.types import Attributes, Severity


def _current_trace_span_ids() -> tuple[str | None, str | None]:
    try:
        span = otel_trace.get_current_span()
        ctx = span.get_span_context()
        if not getattr(ctx, "is_valid", False):
            return None, None
        trace_id = format(int(ctx.trace_id), "032x")
        span_id = format(int(ctx.span_id), "016x")
        return trace_id, span_id
    except Exception:
        return None, None


class OtelLogger(LoggerPort):
    def __init__(
        self,
        *,
        schema_version: str,
        min_severity: Severity,
        console: ConsoleRenderer,
        format: str = "pretty",  # pretty | json
        allowed_channels: set[str] | None = None,
        logger_name: str | None = None,
    ) -> None:
        self._schema_version = schema_version
        self._min_severity = min_severity
        self._console = console
        self._format = (format or "pretty").lower()
        self._allowed_channels = allowed_channels or None
        self._logger_name = logger_name
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

        trace_id, span_id = _current_trace_span_ids()

        attrs: dict[str, Any] = dict(attributes or {})
        attrs[semconv.TYCHERION_SCHEMA_VERSION] = self._schema_version
        if self._logger_name:
            attrs.setdefault("tycherion.logger", self._logger_name)

        channel = attrs.get(semconv.ATTR_CHANNEL)
        if self._allowed_channels is not None:
            if channel is None:
                return
            if str(channel) not in self._allowed_channels:
                return

        if self._format == "json":
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": severity.value,
                "body": body,
                "attributes": attrs,
                "trace_id": trace_id,
                "span_id": span_id,
            }
            try:
                import json

                print(json.dumps(payload, ensure_ascii=False))
            except Exception:
                # fallback to console if JSON fails
                self._console.log(
                    body=body,
                    severity=severity,
                    attributes=attrs,
                    trace_id=trace_id,
                    span_id=span_id,
                )
        else:
            self._console.log(
                body=body,
                severity=severity,
                attributes=attrs,
                trace_id=trace_id,
                span_id=span_id,
            )


class OtelLoggerProvider(LoggerProviderPort):
    def __init__(
        self,
        *,
        schema_version: str,
        min_severity: Severity,
        console: ConsoleRenderer,
        format: str = "pretty",
        allowed_channels: set[str] | None = None,
    ) -> None:
        self._schema_version = schema_version
        self._min_severity = min_severity
        self._console = console
        self._format = format
        self._allowed_channels = allowed_channels

    def get_logger(self, name: str, version: str | None = None) -> LoggerPort:
        _ = (name, version)
        return OtelLogger(
            schema_version=self._schema_version,
            min_severity=self._min_severity,
            console=self._console,
            format=self._format,
            allowed_channels=self._allowed_channels,
            logger_name=name or None,
        )
