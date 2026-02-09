from __future__ import annotations

from typing import Protocol, runtime_checkable

from .logs import LoggerProviderPort
from .metrics import MeterProviderPort
from .traces import TracerProviderPort


@runtime_checkable
class ObservabilityPort(Protocol):
    @property
    def traces(self) -> TracerProviderPort: ...

    @property
    def logs(self) -> LoggerProviderPort: ...

    @property
    def metrics(self) -> MeterProviderPort: ...

    def shutdown(self) -> None: ...
    def force_flush(self) -> None: ...
