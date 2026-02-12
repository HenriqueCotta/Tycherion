# Configuration Reference

Audience: developers and operators.
Goal: canonical configuration contract for Tycherion.

## Canonical Root Keys
- `timeframe`
- `lookback_days`
- `trading`
- `risk`
- `mt5`
- `application`
- `observability` (canonical)
- `telemetry` (deprecated alias, backward-compatible)

## Root Keys
| Path | Type | Required | Default | Example |
| --- | --- | --- | --- | --- |
| `timeframe` | string | yes | - | `H1` |
| `lookback_days` | int | yes | - | `15` |
| `trading` | object | no | see section | `{...}` |
| `risk` | object | no | see section | `{...}` |
| `mt5` | object | no | see section | `{...}` |
| `application` | object | no | see section | `{...}` |
| `observability` | object | no | see section | `{...}` |
| `telemetry` | object | no | deprecated alias | `{...}` |

## `trading`
| Path | Type | Default | Notes |
| --- | --- | --- | --- |
| `trading.dry_run` | bool | `true` | disables real order placement |
| `trading.require_demo` | bool | `true` | blocks non-demo account use |
| `trading.deviation_points` | int | `10` | broker slippage tolerance |
| `trading.volume_mode` | string | `min` | `min` or `fixed` |
| `trading.fixed_volume` | float | `0.01` | ignored unless `trading.volume_mode=fixed` |

## `risk`
| Path | Type | Default | Notes |
| --- | --- | --- | --- |
| `risk.risk_per_trade_pct` | float | `0.5` | not enforced yet in current runtime path |
| `risk.max_daily_loss_pct` | float | `2.0` | not enforced yet in current runtime path |

## `mt5`
| Path | Type | Default | Notes |
| --- | --- | --- | --- |
| `mt5.terminal_path` | string\|null | `null` | can be loaded from env |
| `mt5.server` | string\|null | `null` | can be loaded from env |
| `mt5.login` | int\|null | `null` | can be loaded from env |
| `mt5.password` | string\|null | `null` | can be loaded from env |

## `application`
| Path | Type | Default | Notes |
| --- | --- | --- | --- |
| `application.run_mode.name` | string | `live_multimodel` | current supported mode |
| `application.playbook` | string | `default` | indicator selection tag context |
| `application.schedule.run_forever` | bool | `false` | continuous loop toggle |
| `application.schedule.interval_seconds` | int | `60` | loop interval |
| `application.coverage.source` | string | `market_watch` | `static`, `market_watch`, `pattern` |
| `application.coverage.symbols` | string[] | `[]` | used for `static` |
| `application.coverage.pattern` | string\|null | `null` | used for `pattern` |
| `application.models.pipeline` | string[]\|object[] | `[]` | ordered model stages |
| `application.portfolio.allocator` | string | `proportional` | plugin name |
| `application.portfolio.balancer` | string | `threshold` | plugin name |
| `application.portfolio.threshold_weight` | float | `0.25` | canonical rebalance threshold path |

Pipeline object mode example (copy/paste):
```yaml
application:
  playbook: default
  models:
    pipeline:
      - name: trend_following
        drop_threshold: 0.15
      - name: mean_reversion
        drop_threshold: 0.05
```

## Runtime Enforcement Status
- `risk.*` is loaded by config but not enforced yet in live execution.
- Current runtime path: `src/tycherion/application/runmodes/live_multimodel.py`.
- Planned enforcement location: pre-order guard in the application service layer before `build_orders(...)`.
- Track future enforcement explicitly through ADR updates before changing semantics.

## `observability`
See dedicated page: [Observability Config](./observability/config.md).

## Environment Overrides
- MT5: `MT5_TERMINAL_PATH`, `MT5_SERVER`, `MT5_LOGIN`, `MT5_PASSWORD`
- Observability: `TYCHERION_OTLP_ENABLED`, `TYCHERION_OTLP_ENDPOINT`, `TYCHERION_OTLP_PROTOCOL`, `TYCHERION_OTLP_HEADERS`, `TYCHERION_OTLP_INSECURE`, `TYCHERION_DEPLOYMENT_ENV`, `TYCHERION_LOG_FORMAT`, `TYCHERION_CONSOLE_ENABLED`, `TYCHERION_CONSOLE_MIN_LEVEL`, `TYCHERION_CONSOLE_CHANNELS`

## Pitfalls
- Prefer `observability`, not deprecated `telemetry`.
- Use canonical threshold path: `application.portfolio.threshold_weight`.
- `trading.fixed_volume` has no effect when `trading.volume_mode=min`.
- Keep credentials out of versioned files.

## Links
- Next: [Config Execution Map](./config-execution-map.md)
- See also: [Critical Invariants](./critical-invariants.md)
