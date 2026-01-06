from __future__ import annotations

import json
from dataclasses import dataclass, field

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetrySink


# Idempotent-ish DDL:
# - Create table if missing
# - Add new columns for newer schema if table existed from older versions
# - Create a unique index for idempotent dedupe (trace_id, event_seq)
_DDL = """
CREATE TABLE IF NOT EXISTS execution_journal_events (
  id BIGSERIAL PRIMARY KEY,
  runner_id TEXT NULL,
  trace_id TEXT NOT NULL,
  event_seq BIGINT NULL,
  ts_utc TEXT NOT NULL,
  mono_ns BIGINT NULL,
  span_id TEXT NULL,
  parent_span_id TEXT NULL,
  name TEXT NOT NULL,
  level TEXT NOT NULL,
  channel TEXT NOT NULL,
  attributes_json TEXT NOT NULL,
  data_json TEXT NOT NULL,
  schema_version INTEGER NOT NULL
);

ALTER TABLE execution_journal_events ADD COLUMN IF NOT EXISTS runner_id TEXT NULL;
ALTER TABLE execution_journal_events ADD COLUMN IF NOT EXISTS event_seq BIGINT NULL;
ALTER TABLE execution_journal_events ADD COLUMN IF NOT EXISTS mono_ns BIGINT NULL;

CREATE INDEX IF NOT EXISTS idx_eje_trace_ts ON execution_journal_events(trace_id, ts_utc);
CREATE INDEX IF NOT EXISTS idx_eje_span ON execution_journal_events(span_id);
CREATE INDEX IF NOT EXISTS idx_eje_name ON execution_journal_events(name);
CREATE INDEX IF NOT EXISTS idx_eje_channel ON execution_journal_events(channel);
CREATE INDEX IF NOT EXISTS idx_eje_runner ON execution_journal_events(runner_id);

-- Dedupe / idempotency
CREATE UNIQUE INDEX IF NOT EXISTS uq_eje_trace_eventseq ON execution_journal_events(trace_id, event_seq);
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

    Dedupe strategy:
    - table has a surrogate PK (BIGSERIAL)
    - for idempotency, we also have a unique index on (trace_id, event_seq)
    - inserts use ON CONFLICT DO NOTHING when supported
    """

    dsn: str
    enabled_flag: bool = True
    channels: set[str] = field(default_factory=lambda: {"audit", "ops"})
    min_level: TelemetryLevel = TelemetryLevel.INFO
    batch_size: int = 100

    _conn: object | None = field(default=None, init=False, repr=False)
    _buffer: list[
        tuple[
            str | None,
            str,
            int | None,
            str,
            int | None,
            str | None,
            str | None,
            str,
            str,
            str,
            str,
            str,
            int,
        ]
    ] = field(default_factory=list, init=False, repr=False)
    _supports_on_conflict: bool = field(default=True, init=False, repr=False)

    def _ensure_conn(self):
        if self._conn is not None:
            return self._conn
        conn = _connect(self.dsn)
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
            attributes_json = json.dumps(
                dict(event.attributes or {}), separators=(",", ":"), ensure_ascii=False
            )
            data_json = json.dumps(dict(event.data or {}), separators=(",", ":"), ensure_ascii=False)
            row = (
                str(event.runner_id) if event.runner_id else None,
                str(event.trace_id),
                int(event.event_seq) if event.event_seq is not None else None,
                event.ts_utc.isoformat(),
                int(event.mono_ns) if event.mono_ns is not None else None,
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
            return

    def flush(self) -> None:
        if not self._buffer:
            return
        try:
            conn = self._ensure_conn()
        except Exception:
            self._buffer.clear()
            return

        rows = list(self._buffer)
        self._buffer.clear()

        def _exec(sql: str) -> None:
            cur = conn.cursor()
            cur.executemany(sql, rows)
            conn.commit()

        try:
            if self._supports_on_conflict:
                _exec(
                    """
                    INSERT INTO execution_journal_events
                      (runner_id, trace_id, event_seq, ts_utc, mono_ns, span_id, parent_span_id, name, level, channel, attributes_json, data_json, schema_version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (trace_id, event_seq) DO NOTHING
                    """
                )
            else:
                _exec(
                    """
                    INSERT INTO execution_journal_events
                      (runner_id, trace_id, event_seq, ts_utc, mono_ns, span_id, parent_span_id, name, level, channel, attributes_json, data_json, schema_version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                )
        except Exception:
            # If ON CONFLICT fails (missing unique index/constraint), fallback once.
            try:
                conn.rollback()
            except Exception:
                pass

            if self._supports_on_conflict:
                self._supports_on_conflict = False
                try:
                    _exec(
                        """
                        INSERT INTO execution_journal_events
                          (runner_id, trace_id, event_seq, ts_utc, mono_ns, span_id, parent_span_id, name, level, channel, attributes_json, data_json, schema_version)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                    )
                    return
                except Exception:
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
