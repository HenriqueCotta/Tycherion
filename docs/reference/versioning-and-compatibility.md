# Versioning and Compatibility

Audience: maintainers and contributors changing contracts.
Goal: define how Tycherion evolves config and behavior without breaking users unexpectedly.

## Scope

This page governs compatibility for:

- configuration keys and path names
- deprecated aliases
- behavior changes affecting runtime contracts

## Compatibility Rules

1. Canonical key/path changes require ADR.
2. Deprecated aliases must be explicitly documented in `reference/configuration.md`.
3. If alias support remains in code, docs must state deprecation status and migration target.
4. Breaking behavior changes require:

- ADR update
- reference contract update
- explicit migration note

## Deprecation Policy

- Mark as deprecated in docs first.
- Keep backward compatibility for at least one documented migration window.
- Emit warning in runtime loader where practical.
- Remove alias only after ADR and contract update.

Current example:

- canonical key: `observability`
- deprecated alias: `telemetry`
- source: `src/tycherion/shared/config.py` and [ADR-0001](../architecture/decisions/adr-0001-observability-naming.md)

## Release Checklist for Contract Changes

- [ ] ADR updated or created.
- [ ] Reference pages updated.
- [ ] Config example (`configs/demo.yaml`) still loads.
- [ ] `scripts/check_docs.ps1` passes.
- [ ] Safe migration note included.

## Links

- Next: [Configuration Reference](./configuration.md)
- See also: [Documentation Standards](./documentation-standards.md)
