from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from tycherion.ports.observability.types import Severity


def _mongo_client(uri: str):
    try:
        from pymongo import MongoClient  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Mongo audit sink requires `pymongo` to be installed in the runtime environment"
        ) from e
    return MongoClient(uri)


@dataclass(slots=True)
class MongoOpsJournal:
    """Append-only ops journal persisted in MongoDB.

    Stores logs and span events in a single collection for easy filtering.

    Dedupe strategy:
    - unique index on (trace_id, event_seq) when available
    - inserts are best-effort, duplicates are ignored
    """

    uri: str
    db_name: str = "tycherion"
    collection_name: str = "ops_journal"
    enabled_flag: bool = True
    min_severity: Severity = Severity.INFO
    batch_size: int = 200

    runner_id: str | None = None
    schema_version: str | None = None

    _client: Any | None = field(default=None, init=False, repr=False)
    _collection: Any | None = field(default=None, init=False, repr=False)
    _buffer: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def _ensure_collection(self):
        if self._collection is not None:
            return self._collection

        client = _mongo_client(self.uri)
        db = client[self.db_name]
        col = db[self.collection_name]

        try:
            col.create_index([("trace_id", 1), ("event_seq", 1)], unique=True, name="uq_trace_eventseq")
            col.create_index([("ts_utc", 1)], name="idx_ts")
            col.create_index([("runner_id", 1)], name="idx_runner")
            col.create_index([("severity", 1)], name="idx_severity")
            col.create_index([("signal", 1)], name="idx_signal")
        except Exception:
            pass

        self._client = client
        self._collection = col
        return col

    def _rank(self, s: Severity) -> int:
        return {
            Severity.TRACE: 0,
            Severity.DEBUG: 10,
            Severity.INFO: 20,
            Severity.WARN: 30,
            Severity.ERROR: 40,
            Severity.FATAL: 50,
        }[s]

    def enabled(self, severity: Severity) -> bool:
        if not self.enabled_flag:
            return False
        return self._rank(severity) >= self._rank(self.min_severity)

    def emit_log(
        self,
        *,
        body: str,
        severity: Severity,
        attributes: Mapping[str, Any] | None,
        trace_id: str | None,
        span_id: str | None,
        event_seq: int | None,
    ) -> None:
        if not self.enabled(severity):
            return

        doc: dict[str, Any] = {
            "signal": "log",
            "ts_utc": datetime.now(timezone.utc),
            "runner_id": self.runner_id,
            "schema_version": self.schema_version,
            "severity": severity.value,
            "body": body,
            "attributes": dict(attributes or {}),
            "trace_id": trace_id,
            "span_id": span_id,
            "event_seq": event_seq,
        }
        self._buffer.append(doc)
        if len(self._buffer) >= max(1, int(self.batch_size)):
            self.flush()

    def emit_span_event(
        self,
        *,
        name: str,
        attributes: Mapping[str, Any] | None,
        trace_id: str | None,
        span_id: str | None,
        event_seq: int | None,
    ) -> None:
        # Span events are considered INFO.
        if not self.enabled(Severity.INFO):
            return

        doc: dict[str, Any] = {
            "signal": "span_event",
            "ts_utc": datetime.now(timezone.utc),
            "runner_id": self.runner_id,
            "schema_version": self.schema_version,
            "severity": Severity.INFO.value,
            "name": name,
            "attributes": dict(attributes or {}),
            "trace_id": trace_id,
            "span_id": span_id,
            "event_seq": event_seq,
        }
        self._buffer.append(doc)
        if len(self._buffer) >= max(1, int(self.batch_size)):
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        try:
            col = self._ensure_collection()
        except Exception:
            self._buffer.clear()
            return

        docs = list(self._buffer)
        self._buffer.clear()

        try:
            col.insert_many(docs, ordered=False)
        except Exception:
            return

    def close(self) -> None:
        try:
            self.flush()
        finally:
            try:
                if self._client is not None:
                    self._client.close()
            except Exception:
                pass
            self._client = None
            self._collection = None
