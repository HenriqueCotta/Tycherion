from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import sys
from typing import Any, Mapping

from tycherion.ports.observability.types import Severity


@dataclass(slots=True)
class ConsoleConfig:
    enabled: bool = True
    min_severity: Severity = Severity.INFO
    show_span_lifecycle: bool = True


class ConsoleRenderer:
    def __init__(self, cfg: ConsoleConfig) -> None:
        self._cfg = cfg
        self._rank = {
            Severity.TRACE: 0,
            Severity.DEBUG: 10,
            Severity.INFO: 20,
            Severity.WARN: 30,
            Severity.ERROR: 40,
            Severity.FATAL: 50,
        }

    def enabled_for(self, sev: Severity) -> bool:
        if not self._cfg.enabled:
            return False
        return self._rank[sev] >= self._rank[self._cfg.min_severity]

    def _short(self, hex_id: str | None) -> str | None:
        if not hex_id:
            return None
        return hex_id[:8]

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _fmt_kv(self, attrs: Mapping[str, Any] | None) -> str:
        if not attrs:
            return ""
        items = []
        for k, v in attrs.items():
            if v is None:
                continue
            items.append(f"{k}={v}")
        return " ".join(items)

    def log(self, *, body: str, severity: Severity, attributes: Mapping[str, Any] | None, trace_id: str | None, span_id: str | None) -> None:
        if not self.enabled_for(severity):
            return
        meta = []
        if trace_id:
            meta.append(f"trace={trace_id if severity in (Severity.ERROR, Severity.FATAL) else self._short(trace_id)}")
        if span_id:
            meta.append(f"span={self._short(span_id)}")
        meta_s = (" | " + " ".join(meta)) if meta else ""
        attrs_s = self._fmt_kv(attributes)
        attrs_s = (attrs_s + " ") if attrs_s else ""
        line = f"{self._ts()} [{severity.value}] {attrs_s}{body}{meta_s}"
        print(line, file=sys.stdout)

    def span_started(self, *, name: str, attributes: Mapping[str, Any] | None, trace_id: str, span_id: str) -> None:
        if not (self._cfg.enabled and self._cfg.show_span_lifecycle):
            return
        meta = f"trace={self._short(trace_id)} span={self._short(span_id)}"
        attrs_s = self._fmt_kv(attributes)
        attrs_s = (attrs_s + " ") if attrs_s else ""
        print(f"{self._ts()} [SPAN] {attrs_s}{name} started | {meta}", file=sys.stdout)

    def span_ended(self, *, name: str, status: str, duration_ms: float | None, trace_id: str, span_id: str, error: bool) -> None:
        if not (self._cfg.enabled and self._cfg.show_span_lifecycle):
            return
        dur = f"{duration_ms:.1f}ms" if duration_ms is not None else "?"
        # If error, print full trace_id to make backend lookup easy.
        trace_meta = trace_id if error else self._short(trace_id)
        meta = f"trace={trace_meta} span={self._short(span_id)}"
        print(f"{self._ts()} [SPAN] {name} ended status={status} dur={dur} | {meta}", file=sys.stdout)

    def span_event(self, *, name: str, attributes: Mapping[str, Any] | None, trace_id: str | None, span_id: str | None) -> None:
        # Span events are usually info-ish, but we still respect min_severity (INFO).
        if not self.enabled_for(Severity.INFO):
            return
        meta = []
        if trace_id:
            # Span events don't carry severity. Keep output short by default.
            meta.append(f"trace={self._short(trace_id)}")
        if span_id:
            meta.append(f"span={self._short(span_id)}")
        meta_s = (" | " + " ".join(meta)) if meta else ""
        attrs_s = self._fmt_kv(attributes)
        attrs_s = (attrs_s + " ") if attrs_s else ""
        print(f"{self._ts()} [EVT] {attrs_s}{name}{meta_s}", file=sys.stdout)
