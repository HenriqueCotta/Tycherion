from __future__ import annotations

from typing import Any, Mapping

from opentelemetry import trace as otel_trace

from tycherion.adapters.observability.otel.console import ConsoleRenderer
from tycherion.adapters.observability.otel.event_seq import EventSeqManager
from tycherion.adapters.observability.otel.mongo_audit import MongoOpsJournal
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
        event_seq: EventSeqManager,
        mongo: MongoOpsJournal | None,
    ) -> None:
        self._schema_version = schema_version
        self._min_severity = min_severity
        self._console = console
        self._event_seq = event_seq
        self._mongo = mongo
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

        seq = None
        if trace_id:
            seq = self._event_seq.next_for_trace(trace_id)

        attrs: dict[str, Any] = dict(attributes or {})
        attrs["tycherion.schema_version"] = self._schema_version
        if seq is not None:
            attrs["tycherion.event_seq"] = seq

        self._console.log(
            body=body,
            severity=severity,
            attributes=attrs,
            trace_id=trace_id,
            span_id=span_id,
            event_seq=seq,
        )

        if self._mongo is not None:
            self._mongo.emit_log(
                body=body,
                severity=severity,
                attributes=attrs,
                trace_id=trace_id,
                span_id=span_id,
                event_seq=seq,
            )


class OtelLoggerProvider(LoggerProviderPort):
    def __init__(
        self,
        *,
        schema_version: str,
        min_severity: Severity,
        console: ConsoleRenderer,
        event_seq: EventSeqManager,
        mongo: MongoOpsJournal | None,
    ) -> None:
        self._schema_version = schema_version
        self._min_severity = min_severity
        self._console = console
        self._event_seq = event_seq
        self._mongo = mongo

    def get_logger(self, name: str, version: str | None = None) -> LoggerPort:
        # name/version are carried in OTel "instrumentation scope". For now, we keep them for
        # API compatibility and future wiring into OTel Logs SDK.
        _ = (name, version)
        return OtelLogger(
            schema_version=self._schema_version,
            min_severity=self._min_severity,
            console=self._console,
            event_seq=self._event_seq,
            mongo=self._mongo,
        )
