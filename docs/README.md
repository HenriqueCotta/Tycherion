# Tycherion Documentation

This documentation follows a stable structure used in mature engineering organizations:
`Overview -> Guides -> Reference -> Runbooks -> Decisions`.

## Start Here

- Platform overview: [Architecture Overview](./architecture/overview.md)
- 10-minute setup: [Quickstart](./guides/quickstart.md)
- Production operations: [Operations](./guides/operations.md)
- Documentation policy: [Documentation Standards](./reference/documentation-standards.md)

## Information Architecture

- `architecture/`: system explanations and layer boundaries.
- `concepts/`: domain vocabulary and mental models.
- `guides/`: task-oriented procedures.
- `reference/`: canonical contracts and stable specifications.
- `runbooks/`: incident response and recovery procedures.
- `architecture/decisions/`: ADRs for cross-cutting technical decisions.
- `diagrams/`: Mermaid source files consumed by documentation pages.

## Read Paths

- New developer: `guides/quickstart.md` -> `architecture/overview.md` -> `architecture/pipeline.md` -> `reference/configuration.md` -> `guides/operations.md`
- First narrative tutorial: `guides/tutorial-first-end-to-end-cycle.md` -> `reference/execution-contract.md` -> `guides/safe-changes-playbook.md`
- Trading and MT5 onboarding: `concepts/trading-mt5-fundamentals.md` -> `concepts/risk-sizing-churn.md` -> `runbooks/mt5-connectivity-auth.md`
- Safe system changes: `reference/critical-invariants.md` -> `reference/ports-contracts.md` -> `reference/execution-contract.md` -> `reference/config-execution-map.md`
- Pre-PR safety path: `guides/safe-changes-playbook.md` -> `reference/critical-invariants.md` -> `reference/documentation-standards.md`
- Contract evolution path: `reference/versioning-and-compatibility.md` -> `architecture/decisions/adr-0001-observability-naming.md` -> `reference/configuration.md`
- Strategy and plugin work: `concepts/risk-sizing-churn.md` -> `reference/plugins.md` -> `reference/development.md`
- Observability work: `guides/observability.md` -> `architecture/observability.md` -> `reference/observability/instrumentation.md` -> `runbooks/observability.md`
- Decision history: `architecture/decisions/README.md`

## Standards

- Every guide includes: expected outcome, prerequisites, steps, validation, rollback, links.
- Every reference includes: canonical contracts, defaults, examples, pitfalls.
- Every architecture page includes: purpose, boundaries, critical flow, extension points, related ADRs.
- Every runbook includes: symptoms, checks, mitigation, rollback, escalation, code pointers, links.

## Mermaid Usage

- Render diagrams directly inside `.md` pages using ` ```mermaid ` blocks.
- Keep diagram source of truth in `docs/diagrams/*.mmd`.
- Every diagrammed page includes a `Diagram source:` markdown link to its `.mmd` file.

## Folder Indexes

- Guides index: [Guides README](./guides/README.md)
- Reference index: [Reference README](./reference/README.md)
- Runbooks index: [Runbooks README](./runbooks/README.md)
- Concepts index: [Concepts README](./concepts/README.md)
