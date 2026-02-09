from __future__ import annotations

from enum import Enum
from typing import Mapping, Sequence, Union

# OpenTelemetry attribute values are limited to primitives and sequences of primitives.
AttributePrimitive = Union[bool, str, int, float]
AttributeValue = Union[AttributePrimitive, Sequence[AttributePrimitive]]
Attributes = Mapping[str, AttributeValue]

# NOTE:
# Tycherion schema version for observability payloads. Keep stable and explicit.
TYCHERION_SCHEMA_VERSION = "v3"


class Severity(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"

    def to_logging_level(self) -> int:
        import logging

        return {
            Severity.TRACE: 5,  # custom level (below DEBUG)
            Severity.DEBUG: logging.DEBUG,
            Severity.INFO: logging.INFO,
            Severity.WARN: logging.WARNING,
            Severity.ERROR: logging.ERROR,
            Severity.FATAL: logging.CRITICAL,
        }[self]


class SpanStatus(str, Enum):
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"
