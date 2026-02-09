from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opentelemetry import metrics as otel_metrics_api
from opentelemetry import trace as otel_trace

from tycherion.adapters.observability.otel.console import ConsoleConfig, ConsoleRenderer
from tycherion.adapters.observability.otel.event_seq import EventSeqManager
from tycherion.adapters.observability.otel.mongo_audit import MongoOpsJournal
from tycherion.adapters.observability.otel.otel_logs import OtelLoggerProvider
from tycherion.adapters.observability.otel.otel_metrics import OtelMeterProvider
from tycherion.adapters.observability.otel.otel_traces import OtelTracerProvider
from tycherion.ports.observability.observability import ObservabilityPort
from tycherion.ports.observability.traces import TracerProviderPort
from tycherion.ports.observability.logs import LoggerProviderPort
from tycherion.ports.observability.metrics import MeterProviderPort
from tycherion.ports.observability.types import Severity


@dataclass(slots=True)
class OtelObservabilityConfig:
    runner_id: str
    schema_version: str

    # Console output
    console_enabled: bool = True
    console_min_severity: Severity = Severity.INFO
    console_show_span_lifecycle: bool = True

    # OTLP (future: Alloy/Collector -> Tempo/Loki/Prometheus)
    otlp_enabled: bool = False
    otlp_endpoint: str = "http://localhost:4317"

    # Mongo ops journal (optional)
    mongo_audit_enabled: bool = False
    mongo_uri: str | None = None
    mongo_db: str = "tycherion"
    mongo_collection: str = "ops_journal"
    mongo_min_severity: Severity = Severity.INFO
    mongo_batch_size: int = 200


class OtelObservability(ObservabilityPort):
    def __init__(self, cfg: OtelObservabilityConfig) -> None:
        self._cfg = cfg
        self._event_seq = EventSeqManager()

        self._console = ConsoleRenderer(
            ConsoleConfig(
                enabled=bool(cfg.console_enabled),
                min_severity=cfg.console_min_severity,
                show_span_lifecycle=bool(cfg.console_show_span_lifecycle),
            )
        )

        self._mongo: MongoOpsJournal | None = None
        if cfg.mongo_audit_enabled:
            if not cfg.mongo_uri:
                raise ValueError("mongo_audit_enabled=True requires mongo_uri")
            self._mongo = MongoOpsJournal(
                uri=cfg.mongo_uri,
                db_name=cfg.mongo_db,
                collection_name=cfg.mongo_collection,
                enabled_flag=True,
                min_severity=cfg.mongo_min_severity,
                batch_size=cfg.mongo_batch_size,
                runner_id=cfg.runner_id,
                schema_version=cfg.schema_version,
            )

        # SDK imports are intentionally delayed so importing this module does not hard-require
        # opentelemetry-sdk until you actually instantiate this adapter.
        try:
            from opentelemetry.sdk.resources import Resource  # type: ignore
            from opentelemetry.sdk.trace import TracerProvider  # type: ignore
            from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "OtelObservability requires `opentelemetry-sdk` to be installed. "
                "Install project dependencies (see requirements/pyproject)."
            ) from e

        resource = Resource.create(
            {
                "service.name": "tycherion",
                "service.instance.id": cfg.runner_id,
                "tycherion.runner_id": cfg.runner_id,
                "tycherion.schema_version": cfg.schema_version,
            }
        )

        tracer_provider = TracerProvider(resource=resource)

        if cfg.otlp_enabled:
            span_exporter = _build_otlp_span_exporter(cfg.otlp_endpoint)
            if span_exporter is not None:
                tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))

        # Register global providers (safe-ish; used by trace context propagation)
        try:
            otel_trace.set_tracer_provider(tracer_provider)
        except Exception:
            # If provider was already set by runtime, keep ours referenced locally anyway.
            pass

        self._sdk_tracer_provider = tracer_provider
        self._traces = OtelTracerProvider(
            tracer_provider,
            schema_version=cfg.schema_version,
            event_seq=self._event_seq,
            console=self._console,
            mongo=self._mongo,
        )

        # Metrics provider (minimal)
        meter_provider = _build_meter_provider(resource=resource, otlp_enabled=cfg.otlp_enabled, otlp_endpoint=cfg.otlp_endpoint)
        try:
            if meter_provider is not None:
                otel_metrics_api.set_meter_provider(meter_provider)
        except Exception:
            pass

        self._sdk_meter_provider = meter_provider
        self._metrics = OtelMeterProvider(meter_provider) if meter_provider is not None else OtelMeterProvider(_NoopMeterProvider())

        self._logs = OtelLoggerProvider(
            schema_version=cfg.schema_version,
            min_severity=cfg.console_min_severity,  # console gate
            console=self._console,
            event_seq=self._event_seq,
            mongo=self._mongo,
        )

    @property
    def traces(self) -> TracerProviderPort:
        return self._traces

    @property
    def logs(self) -> LoggerProviderPort:
        return self._logs

    @property
    def metrics(self) -> MeterProviderPort:
        return self._metrics

    def force_flush(self) -> None:
        try:
            self._sdk_tracer_provider.force_flush()
        except Exception:
            pass
        try:
            if self._sdk_meter_provider is not None:
                self._sdk_meter_provider.force_flush()
        except Exception:
            pass
        try:
            if self._mongo is not None:
                self._mongo.flush()
        except Exception:
            pass

    def shutdown(self) -> None:
        try:
            self.force_flush()
        finally:
            try:
                self._sdk_tracer_provider.shutdown()
            except Exception:
                pass
            try:
                if self._sdk_meter_provider is not None:
                    self._sdk_meter_provider.shutdown()
            except Exception:
                pass
            try:
                if self._mongo is not None:
                    self._mongo.close()
            except Exception:
                pass


def _build_otlp_span_exporter(endpoint: str):
    # Prefer gRPC exporter (4317) by default; fall back to HTTP exporter (4318) when available.
    # We intentionally keep this "best-effort" to avoid hard failures when only one exporter is installed.
    try:
        if ":4318" in endpoint or endpoint.rstrip("/").endswith("4318"):
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore

            return OTLPSpanExporter(endpoint=endpoint)
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore

        return OTLPSpanExporter(endpoint=endpoint, insecure=True)
    except Exception:
        return None


def _build_meter_provider(*, resource: Any, otlp_enabled: bool, otlp_endpoint: str):
    try:
        from opentelemetry.sdk.metrics import MeterProvider  # type: ignore
    except Exception:
        return None

    if not otlp_enabled:
        return MeterProvider(resource=resource)

    try:
        if ":4318" in otlp_endpoint or otlp_endpoint.rstrip("/").endswith("4318"):
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter  # type: ignore
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader  # type: ignore

            reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint))
            return MeterProvider(resource=resource, metric_readers=[reader])

        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter  # type: ignore
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader  # type: ignore

        reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True))
        return MeterProvider(resource=resource, metric_readers=[reader])
    except Exception:
        return MeterProvider(resource=resource)


class _NoopMeterProvider:
    def get_meter(self, name: str, version: str | None = None):
        _ = (name, version)
        return _NoopMeter()


class _NoopMeter:
    def create_counter(self, name: str, unit: str | None = None, description: str | None = None):
        _ = (name, unit, description)
        return _NoopCounter()


class _NoopCounter:
    def add(self, amount: int, attributes: dict | None = None) -> None:
        _ = (amount, attributes)
        return None
