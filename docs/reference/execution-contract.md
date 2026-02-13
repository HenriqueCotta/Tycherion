# Execution Contract

Audience: contributors modifying run modes, pipeline behavior, or operations.
Goal: define what one runtime cycle means, expected observability signals, and what indicates unhealthy execution.

## One-Cycle Definition

A single cycle is the ordered execution in `live_multimodel`:

1. Coverage selection and held-symbol merge.
2. Pipeline execution for all eligible symbols.
3. Allocation generation.
4. Rebalance plan generation.
5. Order planning.
6. Trade execution (or dry-run execution path).

Canonical source: `src/tycherion/application/runmodes/live_multimodel.py`.

## Expected Signals per Cycle

Expected span and event progression:

- Span: `tycherion.run`
- Event: `tycherion.coverage.summary`
- Event: `tycherion.pipeline.run_summary`
- Event: `tycherion.allocator.completed`
- Event: `tycherion.rebalance.plan_built`
- Event: `tycherion.orders.built`

Expected operational logs:

- `pipeline.signal_emitted`
- `trade.executed` (when orders are generated)
- `run.loop_exception` only on failures

Semantic convention source: `src/tycherion/ports/observability/semconv.py`.

## Healthy vs Problematic

Healthy:

- Cycle finishes without `run.exception` or `run.loop_exception`.
- Signal emission is present for symbols with sufficient market data.
- Rebalance count is stable relative to `application.portfolio.threshold_weight`.

Problematic:

- Consecutive `run.loop_exception` logs.
- Large symbol-drop rate caused by data fetch failures.
- Active run mode with missing observability signals.

## Copy/Paste Validation Run

Single-cycle validation command:

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from tycherion.bootstrap.main import run_app; run_app('configs/demo.yaml')"
```

What to verify in output:

- Plugin discovery completed.
- Pipeline stage events and `pipeline.signal_emitted` appear.
- No repeated loop-exception logs.

## Links

- Next: [Config Execution Map](./config-execution-map.md)
- See also: [Critical Invariants](./critical-invariants.md)
