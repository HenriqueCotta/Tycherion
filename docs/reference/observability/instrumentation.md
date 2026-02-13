# Observability Instrumentation

Audience: developers.
Goal: implement consistent traces, logs, and metrics without leaking OTel into core logic.

## If You Need

- Setup and operator flow: [Observability Guide](../../guides/observability.md).
- Architecture boundaries: [Observability Architecture](../../architecture/observability.md).
- Config keys/defaults: [Observability Config Reference](./config.md).
- Incident restoration: [Observability Runbook](../../runbooks/observability.md).

## Rules

- Inject `ObservabilityPort`; do not import `opentelemetry.*` in domain or application code.
- Use semantic names from `ports/observability/semconv.py`.
- Emit logs with `tycherion.channel` in `{ops,audit,debug}`.

## Traces

```python
tracer = observability.traces.get_tracer("tycherion.pipeline", version=TYCHERION_SCHEMA_VERSION)
with tracer.start_as_current_span(
    semconv.SPAN_PIPELINE,
    attributes={"timeframe": cfg.timeframe, "lookback_days": cfg.lookback_days},
):
    ...
```

## Events

```python
span.add_event(
    semconv.EVT_PIPELINE_STAGE_STARTED,
    {"stage": stage_cfg.name, "threshold": float(stage_cfg.drop_threshold or 0)},
)
```

## Logs

```python
logger = observability.logs.get_logger("tycherion.pipeline", version=TYCHERION_SCHEMA_VERSION)
logger.emit(
    "pipeline.signal_emitted",
    Severity.INFO,
    {semconv.ATTR_CHANNEL: "audit", "symbol": symbol, "signed": signed, "confidence": confidence},
)
```

## Metrics

```python
meter = observability.metrics.get_meter("tycherion.pipeline")
counter = meter.create_counter("tycherion.signals.emitted")
counter.add(1, {"symbol": symbol})
```

## Error Pattern

- `span.record_exception(e)`
- `span.set_status_error(str(e))`
- Log `exception_type`, `message`, and stage context.

## Validation Checklist

- Span names follow semconv.
- Logs correlate with trace and span IDs.
- No sensitive data in log payloads.

## Links

- Next: [Observability Runbook](../../runbooks/observability.md)
- See also: [Observability Architecture](../../architecture/observability.md)
