# Trading and MT5 Fundamentals

Audience: developers new to trading systems and MT5.
Goal: explain the minimum real-world constraints that affect safe engineering decisions.

## Why This Page Exists

Tycherion architecture is clean and modular, but execution still depends on broker and platform constraints. Ignoring these constraints creates false assumptions and operational failures.

## Core Trading Terms

- Timeframe: candle interval (`M1`, `M5`, `H1`, `D1`) used for bar aggregation and model inputs.
- OHLCV: open, high, low, close, volume market data per candle.
- Spread: difference between bid and ask; affects effective entry/exit cost.
- Slippage: price difference between expected fill and actual fill.
- Churn: excessive rebalance flips caused by low thresholds or noisy signals.

## MT5 Execution Constraints

- Minimum lot and lot step: each symbol enforces allowed volume granularity.
- Symbol visibility: a symbol may exist but not be visible/tradable in Market Watch.
- Market session: market-closed symbols reject orders even with valid config.
- Account type behavior: netting vs hedging changes how positions aggregate.
- Retcodes: broker/terminal return codes are the first source for execution diagnosis.

## Practical Engineering Implications

- `trading.volume_mode=min` is safest for first validation runs.
- `trading.volume_mode=fixed` is deterministic but must respect symbol lot rules.
- `application.coverage.*` and market-watch visibility directly affect signal universe.
- `application.portfolio.threshold_weight` is a direct lever for churn/cost balance.

## Safe Defaults for New Contributors

1. Start with `dry_run=true`.
2. Keep small static symbol coverage first.
3. Validate one cycle before enabling continuous loop mode.
4. Use runbooks when behavior differs from expected contracts.

## Links

- Next: [Risk, Sizing, and Churn](./risk-sizing-churn.md)
- See also: [MT5 Connectivity and Auth Runbook](../runbooks/mt5-connectivity-auth.md)
