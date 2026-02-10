from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tycherion.adapters.observability.otel.console_dev import ConsoleConfig, ConsoleRenderer
from tycherion.adapters.observability.otel.otel_export import build_metric_reader, build_span_exporter
from tycherion.adapters.observability.otel.otel_resource import build_resource
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
    run_id: str
    schema_version: str

    deployment_env: str | None = None

    # Console output (dev-only)
    console_enabled: bool = True
    console_min_severity: Severity = Severity.INFO
    console_show_span_lifecycle: bool = True
    log_format: str = "pretty"  # pretty | json
    console_channels: set[str] | None = None

    # OTLP (Collector/Alloy)
    otlp_enabled: bool = False
    otlp_endpoint: str = "http://localhost:4317"
    otlp_protocol: str = "grpc"  # grpc | http
    otlp_headers: dict[str, str] | str | None = None
    otlp_insecure: bool | None = None  # None => infer from scheme (http->True, https->False)


class OtelObservability(ObservabilityPort):
    def __init__(self, cfg: OtelObservabilityConfig) -> None:
        self._cfg = cfg

        self._console = ConsoleRenderer(
            ConsoleConfig(
                enabled=bool(cfg.console_enabled),
                min_severity=cfg.console_min_severity,
                show_span_lifecycle=bool(cfg.console_show_span_lifecycle),
            )
        )
        allowed_channels = set(cfg.console_channels) if cfg.console_channels else None

        try:
            from opentelemetry import metrics as otel_metrics_api  # type: ignore
            from opentelemetry import trace as otel_trace  # type: ignore
            from opentelemetry.sdk.trace import TracerProvider  # type: ignore
            from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
            from opentelemetry.sdk.metrics import MeterProvider  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "OtelObservability requires `opentelemetry-sdk` to be installed. "
                "Install project dependencies (see requirements/pyproject)."
            ) from e

        resource = build_resource(
            runner_id=cfg.runner_id,
            run_id=cfg.run_id,
            schema_version=cfg.schema_version,
            deployment_env=cfg.deployment_env,
        )

        tracer_provider = TracerProvider(resource=resource)

        if cfg.otlp_enabled:
            span_exporter = build_span_exporter(cfg.otlp_endpoint, cfg.otlp_protocol, cfg.otlp_headers, cfg.otlp_insecure)
            if span_exporter is not None:
                tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))

        try:
            otel_trace.set_tracer_provider(tracer_provider)
        except Exception:
            pass

        self._sdk_tracer_provider = tracer_provider
        self._traces = OtelTracerProvider(
            tracer_provider,
            schema_version=cfg.schema_version,
            console=self._console,
        )

        metric_reader = None
        if cfg.otlp_enabled:
            metric_reader = build_metric_reader(
                endpoint=cfg.otlp_endpoint,
                protocol=cfg.otlp_protocol,
                headers=cfg.otlp_headers,
                insecure=cfg.otlp_insecure,
            )

        if metric_reader is not None:
            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        else:
            meter_provider = MeterProvider(resource=resource)

        try:
            otel_metrics_api.set_meter_provider(meter_provider)
        except Exception:
            pass

        self._sdk_meter_provider = meter_provider
        self._metrics = OtelMeterProvider(meter_provider)

        self._logs = OtelLoggerProvider(
            schema_version=cfg.schema_version,
            min_severity=cfg.console_min_severity,
            console=self._console,
            format=cfg.log_format,
            allowed_channels=allowed_channels,
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
