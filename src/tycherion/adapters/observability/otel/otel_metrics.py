from __future__ import annotations

from typing import Any

from tycherion.ports.observability.metrics import CounterPort, MeterPort, MeterProviderPort
from tycherion.ports.observability.types import Attributes


class _OtelCounter(CounterPort):
    def __init__(self, counter: Any) -> None:
        self._counter = counter

    def add(self, amount: int, attributes: Attributes | None = None) -> None:
        try:
            self._counter.add(amount, attributes=dict(attributes or {}))
        except Exception:
            return None


class _OtelMeter(MeterPort):
    def __init__(self, meter: Any) -> None:
        self._meter = meter

    def create_counter(self, name: str, unit: str | None = None, description: str | None = None) -> CounterPort:
        try:
            c = self._meter.create_counter(name, unit=unit, description=description)
            return _OtelCounter(c)
        except Exception:
            # Fallback: no-op counter
            return _OtelCounter(counter=_NoopCounter())


class _NoopCounter:
    def add(self, amount: int, attributes: dict | None = None) -> None:
        return None


class OtelMeterProvider(MeterProviderPort):
    def __init__(self, provider: Any) -> None:
        self._provider = provider

    def get_meter(self, name: str, version: str | None = None) -> MeterPort:
        # opentelemetry-python uses instrumentation scope params; keyword names
        # differ across versions. Use positional for maximum compatibility.
        meter = self._provider.get_meter(name, version)
        return _OtelMeter(meter)
