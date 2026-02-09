from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol, runtime_checkable

from .types import Attributes


@runtime_checkable
class SpanPort(Protocol):
    def set_attribute(self, key: str, value: object) -> None: ...
    def set_attributes(self, attributes: Attributes) -> None: ...
    def add_event(self, name: str, attributes: Attributes | None = None) -> None: ...
    def record_exception(self, exc: BaseException) -> None: ...
    def set_status_ok(self) -> None: ...
    def set_status_error(self, message: str | None = None) -> None: ...
    def is_recording(self) -> bool: ...


@runtime_checkable
class TracerPort(Protocol):
    def start_as_current_span(
        self, name: str, attributes: Attributes | None = None
    ) -> AbstractContextManager[SpanPort]:
        ...


@runtime_checkable
class TracerProviderPort(Protocol):
    def get_tracer(self, name: str, version: str | None = None) -> TracerPort: ...
