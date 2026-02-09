from __future__ import annotations

from dataclasses import dataclass
import contextvars


@dataclass(slots=True)
class _EventSeqState:
    trace_id_hex: str
    seq: int = 0


_state: contextvars.ContextVar[_EventSeqState | None] = contextvars.ContextVar("tycherion_event_seq_state", default=None)


class EventSeqManager:
    """Tycherion event_seq kept in contextvars and incremented per active trace."""

    def start_trace(self, trace_id_hex: str) -> contextvars.Token[_EventSeqState | None]:
        return _state.set(_EventSeqState(trace_id_hex=trace_id_hex, seq=0))

    def end_trace(self, token: contextvars.Token[_EventSeqState | None]) -> None:
        _state.reset(token)

    def next_for_trace(self, trace_id_hex: str) -> int | None:
        st = _state.get()
        if st is None or st.trace_id_hex != trace_id_hex:
            return None
        st.seq += 1
        return st.seq

    def current_seq(self, trace_id_hex: str) -> int | None:
        st = _state.get()
        if st is None or st.trace_id_hex != trace_id_hex:
            return None
        return st.seq
