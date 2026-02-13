# Order Execution Failures Runbook

Audience: operators and on-call engineers.
Goal: diagnose and recover when order requests are built but rejected or not executed as expected.

## Symptoms

- Frequent failed `trade.executed` outcomes.
- Unexpected zero orders despite rebalance plans.
- Repeated broker-side execution errors or invalid volume behavior.

## Checks

1. Confirm execution mode and safety flags:

   - `trading.dry_run`
   - `trading.require_demo`

2. Confirm volume settings:

   - `trading.volume_mode`
   - `trading.fixed_volume` (used only for `volume_mode=fixed`)

3. Confirm rebalance sensitivity:

   - `application.portfolio.threshold_weight`

4. Inspect execution logs for side, symbol, volume, and result payload.

## Mitigation

- Set `trading.volume_mode=min` to align with broker lot constraints.
- Increase `application.portfolio.threshold_weight` to reduce noisy orders.
- Keep run in single-cycle mode while validating fixes.

## Rollback

1. Revert to `configs/demo.yaml` baseline.
2. Set `trading.dry_run=true`.
3. Re-run one cycle and confirm stable behavior before re-enabling continuous mode.

## Escalation

- Escalate when execution failures persist after one rollback cycle.
- Include failing symbols, volumes, return payloads, and current trading config.

## Code Investigation Pointers

- `src/tycherion/application/services/order_planner.py`
- `src/tycherion/application/services/sizer.py`
- `src/tycherion/adapters/mt5/trading_mt5.py`

## Links

- Next: [Observability Runbook](./observability.md)
- See also: [Execution Contract](../reference/execution-contract.md)
