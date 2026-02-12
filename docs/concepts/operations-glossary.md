# Operations Glossary

Audience: operators, on-call engineers, and contributors touching runtime behavior.
Goal: define operational and observability terms used in runbooks and troubleshooting.

- `runner_id`: stable instance identity (`TYCHERION_RUNNER_ID`) used for correlation across runs.
- `run_id`: unique execution identifier generated at bootstrap for each application run.
- `config_hash`: stable hash of runtime config emitted in run span attributes.
- Degraded mode: fallback operation where OTLP export is disabled or unavailable but console observability remains.
- OTLP endpoint: network target for logs/traces/metrics export.
- OTLP protocol: transport mode (`grpc` or `http`) used by exporter.
- Trace-log correlation: ability to inspect logs and traces for the same execution context.
- `run.loop_exception`: top-level loop failure event emitted in continuous mode.
- `pipeline.symbol_dropped`: symbol removal event caused by threshold/data conditions.

## Links

- Next: [Observability Guide](../guides/observability.md)
- See also: [Execution Contract](../reference/execution-contract.md)
