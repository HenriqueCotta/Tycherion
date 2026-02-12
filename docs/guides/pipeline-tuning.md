# Pipeline Tuning

Audience: strategy and platform developers.
Goal: tune symbol coverage, stage filtering, and rebalance sensitivity without destabilizing operations.

## Expected Outcome

- Stable cycle time.
- Acceptable signal quality.
- Controlled order churn.

## Prerequisites

- Baseline run works with `configs/demo.yaml`.
- You can run single-cycle mode for validation.

## Key Config Paths

- `application.coverage.source`
- `application.coverage.symbols`
- `application.models.pipeline`
- `application.models.pipeline[].drop_threshold`
- `application.portfolio.threshold_weight`

## Tuning Steps

1. Start with small coverage (`static`) and single-cycle runs.
2. Tune `drop_threshold` by stage to remove weak symbols early.
3. Tune `application.portfolio.threshold_weight` to balance responsiveness versus churn.
4. Expand coverage only after latency and churn are acceptable.

## Validation

- Signal count is non-zero but stable.
- Drop counts are explainable by stage logic.
- Rebalance instructions are not oscillating every cycle.

## Rollback

- Revert to last known good config.
- Run with `run_forever=false` for one validation cycle.

## Links

- Next: [Operations](./operations.md)
- See also: [Pipeline Architecture](../architecture/pipeline.md)
