from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from tycherion.ports.telemetry import TelemetryEvent, TelemetryLevel, TelemetrySink


_DDL = """
CREATE TABLE IF NOT EXISTS execution_journal_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc TEXT NOT NULL,
  run_id TEXT NOT NULL,
  name TEXT NOT NULL,
  level TEXT NOT NULL,
  channel TEXT NOT NULL,
  scope_json TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_eje_run_ts ON execution_journal_events(run_id, ts_utc);
CREATE INDEX IF NOT EXISTS idx_eje_name ON execution_journal_events(name);
CREATE INDEX IF NOT EXISTS idx_eje_channel ON execution_journal_events(channel);
"""


@dataclass(slots=True)
class DbExecutionJournalSink(TelemetrySink):
    """Append-only execution journal persisted in SQLite."""

    db_path: str
    enabled_flag: bool = True
    channels: set[str] = field(default_factory=lambda: {"audit", "ops"})
    min_level: TelemetryLevel = TelemetryLevel.INFO
    batch_size: int = 50

    _conn: sqlite3.Connection | None = field(default=None, init=False, repr=False)
    _buffer: list[tuple[str, str, str, str, str, str, str]] = field(
        default_factory=list, init=False, repr=False
    )

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        p = Path(self.db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.executescript(_DDL)
        conn.commit()
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
        conn = self._ensure_conn()
        scope_json = json.dumps(dict(event.scope or {}), separators=(",", ":"), ensure_ascii=False)
        payload_json = json.dumps(dict(event.payload or {}), separators=(",", ":"), ensure_ascii=False)
        row = (
            event.ts_utc.isoformat(),
            str(event.run_id),
            str(event.name),
            str(event.level.value),
            str(event.channel),
            scope_json,
            payload_json,
        )
        self._buffer.append(row)
        if len(self._buffer) >= max(1, int(self.batch_size)):
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        conn = self._ensure_conn()
        rows = list(self._buffer)
        self._buffer.clear()
        try:
            conn.executemany(
                """
                INSERT INTO execution_journal_events
                  (ts_utc, run_id, name, level, channel, scope_json, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        except Exception:
            # best effort; do not break the run
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
