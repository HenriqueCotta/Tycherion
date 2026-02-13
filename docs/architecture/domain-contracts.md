# Domain Contracts

Audience: strategy and platform engineers.
Goal: explain domain-level invariants for signals, allocations, and rebalance instructions.

## Purpose

Provide a stable interpretation layer for domain entities so strategy changes and runtime changes do not silently alter financial semantics.

## Signal Contracts

- `Signal.signed` represents directional strength in `[-1.0, 1.0]`.
- `Signal.confidence` represents confidence in `[0.0, 1.0]`.
- Positive `signed` implies long bias, negative implies short bias, zero implies neutral.

## Indicator and Model Contracts

- Indicators output `IndicatorOutput(score, features)` where `score` is expected in `[-1.0, 1.0]`.
- Models output `ModelDecision(side, weight, confidence)`:
  - `side` in `{BUY, SELL, HOLD}`
  - `weight` in `[0.0, 1.0]`
  - `confidence` in `[0.0, 1.0]`

## Allocation Contracts

- `TargetAllocation.weights[symbol]` expresses desired exposure in `[-1.0, 1.0]`.
- Positive weight means long exposure.
- Negative weight means short exposure (conceptual domain support).

## Rebalance Contracts

- `RebalanceInstruction.delta_weight = to_weight - from_weight`.
- `side` must align with delta sign:
  - positive delta -> `BUY`
  - negative delta -> `SELL`

## Short Exposure Note

- Domain supports negative weights (short intent).
- Real short execution capability depends on broker/account/instrument constraints in MT5 adapter and account setup.
- Operational validation is required before enabling short-dependent strategies.

## Safety Constraints

- Threshold logic (`application.portfolio.threshold_weight`) gates rebalance noise.
- Held positions can be preserved through stage-drop rules to avoid blind exits.

## Links

- Next: [Critical Invariants](../reference/critical-invariants.md)
- See also: [Execution Contract](../reference/execution-contract.md)
