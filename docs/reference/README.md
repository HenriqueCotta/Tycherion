# Reference

Audience: developers and reviewers.
Goal: provide canonical contracts and stable technical specifications.

## Reference Index

- [Critical Invariants](./critical-invariants.md)
- [Ports Contracts](./ports-contracts.md)
- [Execution Contract](./execution-contract.md)
- [Configuration Reference](./configuration.md)
- [Config Execution Map](./config-execution-map.md)
- [Development Guide](./development.md)
- [Plugins and Registry Reference](./plugins.md)
- [Testing Reference](./testing.md)
- [Versioning and Compatibility](./versioning-and-compatibility.md)
- [Observability Config Reference](./observability/config.md)
- [Observability Instrumentation](./observability/instrumentation.md)
- [Documentation Standards](./documentation-standards.md)

## Navigation Rules

- Use reference docs when you need exact contracts, defaults, type behavior, or resolver rules.
- Use [Safe Changes Playbook](../guides/safe-changes-playbook.md) before high-risk modifications.
- Use [Guides](../guides/README.md) for step-by-step procedures.
- Use [Architecture](../architecture/overview.md) to understand rationale and boundaries.

## Source-of-Truth Hierarchy

1. `reference/` defines contracts and defaults.
2. `critical-invariants.md` lists invariants and points to canonical contracts.
3. `config-execution-map.md` maps runtime consumption without redefining contracts.
