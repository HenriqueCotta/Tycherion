# Safe Changes Playbook

Audience: contributors changing runtime behavior, plugin resolution, config loading, execution, or observability.
Goal: provide one mandatory checklist to ship changes without breaking the trading loop.

## Expected Outcome

- You choose the correct validation path for your change type.
- You run the minimum required checks before opening or merging a PR.
- You know exactly where to look if behavior drifts.

## Prerequisites

- Local environment runs `configs/demo.yaml` successfully.
- Plugin auto-discovery works in your environment.
- Docs checks pass locally.

## Change-Type Checklist

### Pipeline or run mode changes

Run:

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from tycherion.bootstrap.main import run_app; run_app('configs/demo.yaml')"
```

Validate:

- No repeated `run.loop_exception`.
- `pipeline.signal_emitted` events still appear.
- Cycle ordering still matches `coverage -> pipeline -> allocator -> balancer -> order planner -> trader`.

### Plugin registry, model, indicator, allocator, or balancer changes

Run:

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from tycherion.application.plugins.registry import auto_discover, MODELS, ALLOCATORS, BALANCERS; from tycherion.adapters.observability.noop.noop_observability import NoopObservability; auto_discover(observability=NoopObservability()); print('models', sorted(MODELS.keys())); print('allocators', sorted(ALLOCATORS.keys())); print('balancers', sorted(BALANCERS.keys()))"
```

Validate:

- New plugin names are present in registry output.
- Existing canonical plugins are still present.
- Resolver behavior still matches `docs/reference/plugins.md`.

### Config loader or config contract changes

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_docs.ps1 -PythonExe .\.venv\Scripts\python.exe
```

Validate:

- `configs/demo.yaml` loads successfully.
- Canonical paths in docs remain consistent with runtime config model.
- Deprecated aliases remain explicitly documented if still supported.

### Order planning or execution changes

Validate:

- `trading.volume_mode=min` and `trading.volume_mode=fixed` behavior remains distinct.
- `trading.fixed_volume` only affects fixed mode.
- Order side and volumes remain coherent with rebalance instructions.

### Observability changes

Validate:

- Core code still emits through `ObservabilityPort` only.
- OTel initialization failures still degrade safely.
- Console fallback still works when OTLP is unavailable.

## Mandatory Pre-PR Gate

Run before opening PR:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_docs.ps1 -PythonExe .\.venv\Scripts\python.exe
```

Also ensure at least one anchor for every behavior change:

- code link implementing it, or
- test guaranteeing it, or
- ADR documenting future-contract behavior.

## Rollback

- If any mandatory check fails, do not merge.
- Revert the risky config/code delta to last known-good baseline.
- Re-run one-cycle validation and docs checks before reopening PR.

## Links

- Next: [Critical Invariants](../reference/critical-invariants.md)
- See also: [Execution Contract](../reference/execution-contract.md)
