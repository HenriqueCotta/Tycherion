# Risk, Sizing, and Churn

Audience: developers and operators.
Goal: explain practical trade-offs behind risk settings and rebalance behavior.

## Risk

- `risk.risk_per_trade_pct`: not enforced yet in current live execution path.
- `risk.max_daily_loss_pct`: not enforced yet in current live execution path.
- Current path where this is not enforced: `src/tycherion/application/runmodes/live_multimodel.py`.
- Planned enforcement boundary: application service layer before order planning (`build_orders(...)` call site).

## Sizing

- `trading.volume_mode=min`: uses symbol minimum volume, useful for safe validation.
- `trading.volume_mode=fixed`: deterministic lot size via `trading.fixed_volume`.
- Validate sizing per instrument (minimum, step, margin impact).

## Churn

Churn is frequent buy/sell flipping caused by small target-weight changes.

Primary controls:

- `application.portfolio.threshold_weight`
- model noise and stage `drop_threshold`
- coverage size and data quality

Effects of low threshold:

- higher order count
- higher costs and slippage
- noisier PnL

## Practical Sequence

1. Start with `dry_run=true` and small coverage.
2. Increase `application.portfolio.threshold_weight` until churn is acceptable.
3. Tune model thresholds only after execution behavior is stable.

## Links

- Next: [Pipeline Tuning](../guides/pipeline-tuning.md)
- See also: [Configuration Reference](../reference/configuration.md)
