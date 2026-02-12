# Documentation Standards

Audience: maintainers.
Goal: keep docs consistent, navigable, and trustworthy as the project grows.

## Document Classes
- Guide: "how do I do X now?"
- Reference: "what is the exact contract/default/path?"
- Architecture: "why is this designed this way and what are the boundaries?"
- Runbook: "system is failing, how do I restore it?"
- Decision (ADR): "why did we choose this and when can it change?"

## Placement Rules (Constitution)
Use this rule before creating or moving content:
- If it is task execution, place in `guides/`.
- If it is canonical behavior/keys/contracts, place in `reference/`.
- If it is rationale and boundaries, place in `architecture/`.
- If it is incident restoration, place in `runbooks/`.
- If it records a durable technical decision, place in `architecture/decisions/`.

## Subfolder Rules
Create a subfolder only when at least one condition is true:
- Topic has more than 6-8 pages and indexing is hard.
- Topic has self-contained contracts (for example `reference/observability/`).
- Topic has clear ownership boundaries that require separation.

Otherwise keep the folder flat and add a local `README.md` index.

## Required Structure by Page Type
### Guide
- Expected outcome
- Prerequisites
- Steps
- Validation
- Rollback
- Links (`Next` and `See also`)

### Reference
- Canonical contract table (when applicable)
- Semantics and edge cases
- Executable or copy/paste example for common failure points
- Pitfalls
- Links (`Next` and `See also`)

### Architecture
- Purpose
- Boundaries
- Critical flow (diagram when relevant)
- Extension points
- Failure model
- Related ADRs
- Links (`Next` and `See also`)

### Runbook
- Symptoms
- Checks
- Mitigation
- Rollback
- Escalation
- Code pointers
- Links (`Next` and `See also`)

## Diagram Rules
- If a page contains Mermaid, include `Diagram source:` as a markdown link.
- Source of truth diagrams live in `docs/diagrams/*.mmd`.
- Do not keep diverging copies of the same diagram in multiple places.

## "Docs Must Not Lie" Rule
Whenever docs describe behavior, at least one anchor must exist:
- Link to code implementing it.
- Test that guarantees it.
- ADR stating it is a future contract not fully implemented yet.

## Enforcement
- New docs must follow this file.
- Config docs must reflect `AppConfig` and `configs/demo.yaml`.
- `scripts/check_docs.ps1` enforces minimal heading structure by doc class.
- Run local checks before merging:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_docs.ps1 -PythonExe .\.venv\Scripts\python.exe
```

## Human PR Review Checklist
- Content is in the correct doc class/folder by intent.
- Any behavior claim has code link, test anchor, or ADR anchor.
- Config examples do not conflict with documented defaults.
- New runbook-worthy failure modes are reflected in `docs/runbooks/`.

## Links
- Next: [Reference Index](./README.md)
- See also: [Safe Changes Playbook](../guides/safe-changes-playbook.md)
