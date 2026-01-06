from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetrySink


def _mongo_client(uri: str):
    try:
        from pymongo import MongoClient  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "MongoDB telemetry sink requires `pymongo` to be installed in the runtime environment"
        ) from e
    return MongoClient(uri)


@dataclass(slots=True)
class MongoExecutionJournalSink(TelemetrySink):
    """Append-only execution journal persisted in MongoDB.

    This sink is meant for operational health/audit data:
    - errors, spans, lifecycle, audits
    - queryable by trace_id, runner_id, event_seq, time

    Dedupe strategy:
    - unique index on (trace_id, event_seq)
    - inserts are best-effort, duplicates are ignored
    """

    uri: str
    db_name: str = "tycherion"
    collection_name: str = "execution_journal_events"
    enabled_flag: bool = True
    channels: set[str] = field(default_factory=lambda: {"audit", "ops"})
    min_level: TelemetryLevel = TelemetryLevel.INFO
    batch_size: int = 200

    _client: Any | None = field(default=None, init=False, repr=False)
    _collection: Any | None = field(default=None, init=False, repr=False)
    _buffer: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def _ensure_collection(self):
        if self._collection is not None:
            return self._collection

        client = _mongo_client(self.uri)
        db = client[self.db_name]
        col = db[self.collection_name]

        # Best-effort index creation (ignore permissions/duplicate issues)
        try:
            col.create_index([("trace_id", 1), ("event_seq", 1)], unique=True, name="uq_trace_eventseq")
            col.create_index([("ts_utc", 1)], name="idx_ts")
            col.create_index([("runner_id", 1)], name="idx_runner")
            col.create_index([("channel", 1)], name="idx_channel")
            col.create_index([("level", 1)], name="idx_level")
        except Exception:
            pass

        self._client = client
        self._collection = col
        return col

    def enabled(self, channel: str, level: TelemetryLevel, name: str | None = None) -> bool:
        _ = name
        if not self.enabled_flag:
            return False
        if channel not in self.channels:
            return False
        return TelemetryLevel.coerce(level).rank() >= TelemetryLevel.coerce(self.min_level).rank()

    def emit(self, event: TelemetryEvent) -> None:
        if not self.enabled(event.channel, event.level, event.name):
            return

        try:
            doc: dict[str, Any] = {
                "schema_version": int(event.schema_version),
                "runner_id": str(event.runner_id),
                "trace_id": str(event.trace_id),
                "event_seq": int(event.event_seq),
                "ts_utc": event.ts_utc,  # pymongo stores datetime natively
                "mono_ns": int(event.mono_ns) if event.mono_ns is not None else None,
                "span_id": str(event.span_id) if event.span_id else None,
                "parent_span_id": str(event.parent_span_id) if event.parent_span_id else None,
                "name": str(event.name),
                "level": str(event.level.value),
                "channel": str(event.channel),
                "attributes": dict(event.attributes or {}),
                "data": dict(event.data or {}),
            }
            self._buffer.append(doc)
            if len(self._buffer) >= max(1, int(self.batch_size)):
                self.flush()
        except Exception:
            return

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
            # ordered=False keeps going after dup errors
            col.insert_many(docs, ordered=False)
        except Exception:
            # Ignore duplicate key and other errors (best-effort journal)
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
