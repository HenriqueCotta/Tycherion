# Tutorial: First End-to-End Cycle

Audience: developers new to Tycherion and trading workflows.
Goal: run a complete cycle with a minimal config, understand what happens at each stage, and validate outcomes safely.

## Expected Outcome

- You run one full cycle from coverage to execution planning.
- You understand how model pipeline, allocator, and balancer interact.
- You can validate results and roll back safely.

## Prerequisites

- Quickstart environment is working.
- MT5 demo credentials are configured.
- You can run `configs/demo.yaml` without startup errors.

## Steps

1. Create a minimal local config from demo baseline.

   ```powershell
   copy configs\demo.yaml configs\tutorial.yaml
   ```

2. Edit `configs/tutorial.yaml` to use an explicit pipeline object mode and conservative runtime:

   ```yaml
   application:
     schedule:
       run_forever: false
     coverage:
       source: static
       symbols:
         - PETR4
         - VALE3
     models:
       pipeline:
         - name: trend_following
           drop_threshold: 0.10
         - name: mean_reversion
           drop_threshold: 0.05
     portfolio:
       allocator: proportional
       balancer: threshold
       threshold_weight: 0.25
   trading:
     dry_run: true
     require_demo: true
     volume_mode: min
   ```

3. Run one cycle:

   ```powershell
   python -c "from tycherion.bootstrap.main import run_app; run_app('configs/tutorial.yaml')"
   ```

4. Observe expected progression:

   - Coverage built for configured symbols.
   - Pipeline stages run in order with stage events.
   - Allocator builds target weights.
   - Balancer creates rebalance plan using threshold.
   - Order planner prepares orders; trader executes dry-run path.

## Validation

- No repeated `run.loop_exception`.
- At least one `pipeline.signal_emitted` log for symbols with data.
- Rebalance behavior is coherent with `threshold_weight`.

## Rollback

1. Return to baseline:

   ```powershell
   copy configs\demo.yaml configs\tutorial.yaml /Y
   ```

2. Keep `trading.dry_run=true` and rerun one cycle.
3. If issues persist, use [Troubleshooting](./troubleshooting.md) and related runbooks.

## Links

- Next: [Safe Changes Playbook](./safe-changes-playbook.md)
- See also: [Execution Contract](../reference/execution-contract.md)
