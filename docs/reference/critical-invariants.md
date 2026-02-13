# Critical Invariants

Audience: contributors changing runtime, plugins, ports, or configuration.
Goal: provide a single source of truth for high-risk invariants that must hold to change the system safely.

## Canonical Invariants

| Area | Invariant | Source of Truth | Verification Anchor |
| --- | --- | --- | --- |
| Signals | `Signal.signed` stays in `[-1.0, 1.0]`; `Signal.confidence` stays in `[0.0, 1.0]`. | `src/tycherion/domain/portfolio/entities.py` | `docs/reference/execution-contract.md` |
| Model decision mapping | `ModelDecision.side` maps to numeric score with BUY -> `+weight`, SELL -> `-weight`, HOLD -> `0`, clamped to `[-1, 1]`. | `src/tycherion/application/pipeline/service.py` (`_decision_to_score`) | `docs/reference/execution-contract.md` |
| Allocation | `TargetAllocation.weights[symbol]` is portfolio intent in `[-1.0, 1.0]` (negative means short intent). | `src/tycherion/domain/portfolio/entities.py` | `docs/architecture/domain-contracts.md` |
| Rebalance | `RebalanceInstruction.delta_weight = to_weight - from_weight`; `side` must match delta sign. | `src/tycherion/domain/portfolio/entities.py` | `docs/architecture/domain-contracts.md` |
| Config path | Rebalance sensitivity is `application.portfolio.threshold_weight` (canonical path). | `docs/reference/configuration.md`, ADR-0002 | `configs/demo.yaml` load check |
| Observability key | YAML key is `observability`; `telemetry` is deprecated alias for compatibility only. | `src/tycherion/shared/config.py`, ADR-0001 | `docs/reference/observability/config.md` |
| Cycle ordering | One cycle executes `coverage -> pipeline -> allocator -> balancer -> order planner -> trader`. | `src/tycherion/application/runmodes/live_multimodel.py` | `docs/reference/execution-contract.md` |
| Plugin resolution | Indicator resolution follows deterministic rule order (playbook tag, `default`, `DEFAULT_METHOD`, fallback). | `src/tycherion/application/plugins/registry.py` | `docs/reference/plugins.md` |

## Healthy vs Problematic Cycle Signals

Healthy cycle expectations:

- At least one `pipeline.signal_emitted` event when market data is available.
- No repeated `run.loop_exception` emissions.
- Rebalance volume and frequency consistent with `application.portfolio.threshold_weight`.

Problematic cycle patterns:

- Frequent `run.loop_exception` across consecutive cycles.
- Repeated `pipeline.symbol_dropped` due to missing market data.
- No observability signals when runtime is active.

## Contract Change Rule

When changing a behavior documented here, update at least one artifact:

- Code reference that implements the new behavior.
- Test that guarantees the behavior.
- ADR if behavior is future contract (not fully implemented yet).

## Links

- Next: [Ports Contracts](./ports-contracts.md)
- See also: [Execution Contract](./execution-contract.md)
- See also: [Safe Changes Playbook](../guides/safe-changes-playbook.md)
