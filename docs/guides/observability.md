# Observability Guide

Audience: developers, operators, and on-call engineers.
Goal: configure, validate, and operate observability end-to-end.

## If You Need

- Setup and validation steps: stay on this page.
- Capability boundaries and rationale: go to [Observability Architecture](../architecture/observability.md).
- Exact keys and defaults: go to [Observability Config Reference](../reference/observability/config.md).
- Instrumentation patterns: go to [Observability Instrumentation](../reference/observability/instrumentation.md).
- Incident restoration: go to [Observability Runbook](../runbooks/observability.md).

## Expected Outcome

- You understand observability versus telemetry terminology.
- You can configure local and OTLP-backed observability signals.
- You can navigate architecture, reference, and runbook pages quickly.

## Prerequisites

- Base app setup completed: [Quickstart](./quickstart.md)
- Baseline config available (`configs/demo.yaml` or `configs/local.yaml`)

## Terminology

- Observability: capability surface (logs, traces, metrics).
- Telemetry: signal data emitted to support observability.

## Setup Flow

1. Keep `observability` as the canonical YAML key.
2. Enable console output for local diagnostics.
3. Enable OTLP export only after endpoint/protocol is confirmed.
4. Run one cycle and validate logs/spans before continuous loop mode.

## Validation Checklist

- Console emits expected channels (`ops`, `audit`, `debug`) when enabled.
- Pipeline spans and events are visible in collector when OTLP is enabled.
- No recurring `run.loop_exception` related to observability setup.

## Rollback

1. Disable OTLP export (`observability.otlp_enabled=false`).
2. Keep console output enabled for local diagnostics.
3. Validate one cycle before re-enabling OTLP export.

## Links

- Next: [Observability Architecture](../architecture/observability.md)
- See also: [Observability Config Reference](../reference/observability/config.md)
- Incident response: [Observability Runbook](../runbooks/observability.md)
Diagram source: [docs/diagrams/observability_flow.mmd](../diagrams/observability_flow.mmd)
