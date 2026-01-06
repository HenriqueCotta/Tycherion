from __future__ import annotations

import re
from datetime import datetime, timezone


_RUNNER_SAFE_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_runner_id(runner_id: str) -> str:
    """Make runner_id safe to embed into trace_id strings.

    We keep this intentionally conservative: only alnum, dot, underscore, dash.
    """

    runner_id = (runner_id or "").strip()
    if not runner_id:
        return "runner-unknown"
    runner_id = _RUNNER_SAFE_RE.sub("_", runner_id)
    return runner_id[:80]  # keep IDs compact


def format_ts_compact(ts_utc: datetime) -> str:
    """UTC timestamp as YYYYMMDDHHMMSSffffff (microseconds)."""

    if ts_utc.tzinfo is None:
        ts_utc = ts_utc.replace(tzinfo=timezone.utc)
    ts_utc = ts_utc.astimezone(timezone.utc)
    return ts_utc.strftime("%Y%m%d%H%M%S%f")


def make_trace_id(runner_id: str, ts_utc: datetime, trace_seq: int) -> str:
    runner_id = sanitize_runner_id(runner_id)
    return f"{runner_id}-{format_ts_compact(ts_utc)}-{trace_seq:04x}"


def make_span_id(span_seq: int) -> str:
    return f"{span_seq:016x}"
