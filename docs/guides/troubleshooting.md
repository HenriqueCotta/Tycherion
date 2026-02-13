# Troubleshooting

Audience: developers and operators.
Goal: diagnose and recover the most common failures quickly.

## Expected Outcome

- You can identify common failure classes quickly.
- You can apply a safe mitigation and rollback path.

## Prerequisites

- Access to runtime logs and current config.
- Ability to run one-cycle validation mode.

## Symptoms and Checks

### Plugin not found

- Check configured names in `application.models.pipeline` and `application.portfolio.*`.
- Confirm decorator registration in plugin module.

Copy/paste checks:

```powershell
rg -n "@register_model\(name=\"trend_following\"" src/tycherion/domain/signals/models
rg -n "@register_allocator\(name=\"proportional\"" src/tycherion/domain/portfolio/allocators
rg -n "@register_balancer\(name=\"threshold\"" src/tycherion/domain/portfolio/balancers
```

Registry visibility check:

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from tycherion.application.plugins.registry import auto_discover, MODELS, ALLOCATORS, BALANCERS; from tycherion.adapters.observability.noop.noop_observability import NoopObservability; auto_discover(observability=NoopObservability()); print('models', sorted(MODELS.keys())); print('allocators', sorted(ALLOCATORS.keys())); print('balancers', sorted(BALANCERS.keys()))"
```

### No market data

- Validate coverage source and symbols.
- Confirm MT5 connection and timeframe validity.

### Loop exceptions repeating

- Run single-cycle mode (`application.schedule.run_forever=false`).
- Inspect `run.loop_exception` and preceding pipeline events.

### Excessive order churn

- Increase `application.portfolio.threshold_weight`.
- Reduce model noise (pipeline stages and thresholds).

### No observability signals in collector

- Verify `observability.otlp_enabled=true`.
- Check OTLP endpoint, protocol, and network route.

## Mitigation

- Revert to baseline config (`configs/demo.yaml`).
- Force safe mode: `trading.dry_run=true`, `trading.require_demo=true`.

## Rollback

- Undo latest config or code change.
- Validate one cycle before re-enabling continuous mode.

## Escalation

- Escalate if failure persists after one rollback and one single-cycle validation.

## Links

- Next: [Observability Runbook](../runbooks/observability.md)
- See also: [Execution Contract](../reference/execution-contract.md)
- See also: [MT5 Connectivity and Auth Runbook](../runbooks/mt5-connectivity-auth.md)
- See also: [Order Execution Failures Runbook](../runbooks/order-execution-failures.md)
