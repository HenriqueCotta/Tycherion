# Observability Config Reference

Audience: developers and operators.
Goal: canonical configuration for logs, traces, and metrics export.

## If You Need

- Setup steps and validation flow: [Observability Guide](../../guides/observability.md).
- Architecture rationale and boundaries: [Observability Architecture](../../architecture/observability.md).
- Incident restoration: [Observability Runbook](../../runbooks/observability.md).

## Canonical Key

Use `observability` in YAML. `telemetry` is a deprecated alias accepted for compatibility.

## YAML Contract

| Path | Type | Default | Notes |
| --- | --- | --- | --- |
| `observability.console_enabled` | bool | `false` | local stdout output |
| `observability.console_channels` | string[] | `[ops]` | filters by `tycherion.channel` |
| `observability.console_min_level` | string | `INFO` | minimum severity |
| `observability.log_format` | string | `pretty` | `pretty` or `json` |
| `observability.otlp_enabled` | bool | `false` | enables OTLP export |
| `observability.otlp_endpoint` | string | `http://localhost:4317` | collector endpoint |
| `observability.otlp_protocol` | string | `grpc` | `grpc` or `http` |
| `observability.otlp_headers` | string\|null | `null` | auth/metadata headers |
| `observability.otlp_insecure` | bool\|null | `null` | auto-inferred when null |
| `observability.deployment_env` | string\|null | `null` | environment marker |

## Environment Overrides

- `TYCHERION_OTLP_ENABLED`
- `TYCHERION_OTLP_ENDPOINT`
- `TYCHERION_OTLP_PROTOCOL`
- `TYCHERION_OTLP_HEADERS`
- `TYCHERION_OTLP_INSECURE`
- `TYCHERION_DEPLOYMENT_ENV`
- `TYCHERION_LOG_FORMAT`
- `TYCHERION_CONSOLE_ENABLED`
- `TYCHERION_CONSOLE_MIN_LEVEL`
- `TYCHERION_CONSOLE_CHANNELS` (comma-separated list)

## Recommended Profiles

- Dev: console on, `log_format=pretty`, OTLP off.
- Staging: console on, `log_format=json`, OTLP on.
- Prod: `log_format=json`, OTLP on, conservative console channels.

## Pitfalls

- Mismatched endpoint/protocol pair (`grpc` vs `http`).
- Empty `console_channels` can hide logs unexpectedly.
- Keeping credentials in YAML instead of a secret store.

## Links

- Next: [Observability Instrumentation](./instrumentation.md)
- See also: [Observability Runbook](../../runbooks/observability.md)
