# Testing Reference

Audience: developers.
Goal: baseline testing strategy for code and documentation changes.

## Test Pyramid
- Unit: indicators, models, allocators, balancers.
- Service: pipeline behavior with port fakes or stubs.
- Integration (optional): MT5 adapter behavior in controlled demo setup.

## Conventions
- Framework: `pytest`.
- Suggested layout:
  - `tests/domain/...`
  - `tests/application/...`
  - `tests/adapters/...`
- Prefer deterministic fixtures and small in-memory datasets.

## Coverage Targets
- Decision boundaries (`BUY/SELL/HOLD`, threshold edges).
- Error handling paths (missing data, adapter exceptions).
- Config loading behavior for canonical and deprecated keys.

## Documentation Checks
Run docs and config validation script before merge:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_docs.ps1 -PythonExe .\.venv\Scripts\python.exe
```

## When Tests Are Mandatory
- New plugins or resolver behavior changes.
- Run mode and configuration loader changes.
- Changes affecting order generation, thresholds, or scheduling.

## Links
- Next: [Development Guide](./development.md)
- See also: [Documentation Standards](./documentation-standards.md)
