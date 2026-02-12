# Observability Runbook

Audience: operators and on-call engineers.
Goal: restore observability signals and prevent blind operation.

## If You Need...
- Setup or initial validation: [Observability Guide](../guides/observability.md).
- Exact config paths/defaults: [Observability Config Reference](../reference/observability/config.md).
- Architecture rationale: [Observability Architecture](../architecture/observability.md).

## Symptoms
- No traces, logs, or metrics in collector.
- Repeated export errors.
- Missing observability signals during active loop execution.

## Checks
1. Confirm runtime configuration:
- `observability.otlp_enabled`
- `observability.otlp_endpoint`
- `observability.otlp_protocol`
2. Confirm network path to collector.
3. Confirm local console logs still appear (`console_enabled=true`).

## Mitigation
- If collector path is broken, keep console enabled and continue in degraded mode.
- Reduce noise via `console_channels` and `console_min_level`.
- Re-apply last known good observability config.

## Rollback
1. Set `observability.otlp_enabled=false`.
2. Keep `observability.console_enabled=true`.
3. Validate one loop cycle and re-enable OTLP only after endpoint health is confirmed.

## Escalation
- Escalate after 5 minutes with no observability signals in production.
- Include current config, endpoint, last healthy timestamp, and recent deploy or change.

## Code Investigation Pointers
- `src/tycherion/bootstrap/main.py`
- `src/tycherion/adapters/observability/otel/`
- `src/tycherion/ports/observability/semconv.py`

## Links
- Next: [General Troubleshooting](../guides/troubleshooting.md)
- See also: [Observability Architecture](../architecture/observability.md)
