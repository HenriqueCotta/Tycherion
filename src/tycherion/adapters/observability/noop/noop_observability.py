from __future__ import annotations

from contextlib import contextmanager

from tycherion.ports.observability.logs import LoggerPort, LoggerProviderPort
from tycherion.ports.observability.metrics import CounterPort, MeterPort, MeterProviderPort
from tycherion.ports.observability.observability import ObservabilityPort
from tycherion.ports.observability.traces import SpanPort, TracerPort, TracerProviderPort
from tycherion.ports.observability.types import Attributes, Severity


class _NoopSpan(SpanPort):
    def set_attribute(self, key: str, value: object) -> None:
        return None

    def set_attributes(self, attributes: Attributes) -> None:
        return None

    def add_event(self, name: str, attributes: Attributes | None = None) -> None:
        return None

    def record_exception(self, exc: BaseException) -> None:
        return None

    def set_status_ok(self) -> None:
        return None

    def set_status_error(self, message: str | None = None) -> None:
        return None

    def is_recording(self) -> bool:
        return False


class _NoopTracer(TracerPort):
    @contextmanager
    def start_as_current_span(self, name: str, attributes: Attributes | None = None):
        yield _NoopSpan()


class _NoopTracerProvider(TracerProviderPort):
    def get_tracer(self, name: str, version: str | None = None) -> TracerPort:
        return _NoopTracer()


class _NoopLogger(LoggerPort):
    def emit(self, body: str, severity: Severity, attributes: Attributes | None = None) -> None:
        return None

    def is_enabled(self, severity: Severity) -> bool:
        return False


class _NoopLoggerProvider(LoggerProviderPort):
    def get_logger(self, name: str, version: str | None = None) -> LoggerPort:
        return _NoopLogger()


class _NoopCounter(CounterPort):
    def add(self, amount: int, attributes: Attributes | None = None) -> None:
        return None


class _NoopMeter(MeterPort):
    def create_counter(self, name: str, unit: str | None = None, description: str | None = None) -> CounterPort:
        return _NoopCounter()


class _NoopMeterProvider(MeterProviderPort):
    def get_meter(self, name: str, version: str | None = None) -> MeterPort:
        return _NoopMeter()


class NoopObservability(ObservabilityPort):
    def __init__(self) -> None:
        self._traces = _NoopTracerProvider()
        self._logs = _NoopLoggerProvider()
        self._metrics = _NoopMeterProvider()

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
