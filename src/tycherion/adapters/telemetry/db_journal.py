from __future__ import annotations

import json
from dataclasses import dataclass, field

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetrySink


_DDL = """
CREATE TABLE IF NOT EXISTS execution_journal_events (
  id BIGSERIAL PRIMARY KEY,
  ts_utc TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  span_id TEXT NULL,
  parent_span_id TEXT NULL,
  name TEXT NOT NULL,
  level TEXT NOT NULL,
  channel TEXT NOT NULL,
  attributes_json TEXT NOT NULL,
  data_json TEXT NOT NULL,
  schema_version INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_eje_trace_ts ON execution_journal_events(trace_id, ts_utc);
CREATE INDEX IF NOT EXISTS idx_eje_span ON execution_journal_events(span_id);
CREATE INDEX IF NOT EXISTS idx_eje_name ON execution_journal_events(name);
CREATE INDEX IF NOT EXISTS idx_eje_channel ON execution_journal_events(channel);
"""


def _connect(dsn: str):
    """Lazy import of a Postgres driver.

    We intentionally do NOT add dependencies to Tycherion. The sink will work
    if the runtime environment provides a PostgreSQL DB-API driver.
    """

    try:
        import psycopg  # type: ignore

        return psycopg.connect(dsn)
    except Exception:
        pass

    try:
        import psycopg2  # type: ignore

        return psycopg2.connect(dsn)
    except Exception as e:
        raise RuntimeError(
            "PostgreSQL telemetry sink requires a driver (psycopg or psycopg2) to be installed"
        ) from e


@dataclass(slots=True)
class DbExecutionJournalSink(TelemetrySink):
    """Append-only execution journal persisted in PostgreSQL.

    NOTE: This sink uses lazy imports for DB drivers to keep Tycherion dependency-free.
    """

    db_dsn: str
    enabled_flag: bool = True
    channels: set[str] = field(default_factory=lambda: {"audit", "ops"})
    min_level: TelemetryLevel = TelemetryLevel.INFO
    batch_size: int = 100

    _conn: object | None = field(default=None, init=False, repr=False)
    _buffer: list[tuple[str, str, str | None, str | None, str, str, str, str, str, int]] = field(
        default_factory=list, init=False, repr=False
    )

    def _ensure_conn(self):
        if self._conn is not None:
            return self._conn
        conn = _connect(self.db_dsn)
        try:
            cur = conn.cursor()
            cur.execute(_DDL)
            conn.commit()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            raise
        self._conn = conn
        return conn

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
            attributes_json = json.dumps(dict(event.attributes or {}), separators=(",", ":"), ensure_ascii=False)
            data_json = json.dumps(dict(event.data or {}), separators=(",", ":"), ensure_ascii=False)
            row = (
                event.ts_utc.isoformat(),
                str(event.trace_id),
                str(event.span_id) if event.span_id else None,
                str(event.parent_span_id) if event.parent_span_id else None,
                str(event.name),
                str(event.level.value),
                str(event.channel),
                attributes_json,
                data_json,
                int(event.schema_version),
            )
            self._buffer.append(row)
            if len(self._buffer) >= max(1, int(self.batch_size)):
                self.flush()
        except Exception:
            # best effort
            return

    def flush(self) -> None:
        if not self._buffer:
            return
        try:
            conn = self._ensure_conn()
        except Exception:
            # best effort: if we can't connect, drop buffered events
            self._buffer.clear()
            return

        rows = list(self._buffer)
        self._buffer.clear()

        try:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT INTO execution_journal_events
                  (ts_utc, trace_id, span_id, parent_span_id, name, level, channel, attributes_json, data_json, schema_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
            conn.commit()
        except Exception:
            # best effort
            try:
                conn.rollback()
            except Exception:
                pass
            return

    def close(self) -> None:
        try:
            self.flush()
        finally:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
