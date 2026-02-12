# Config Execution Map

Audience: developers and reviewers.
Goal: show where high-impact config fields are consumed at runtime.

## Runtime Mapping
| Config Path | Runtime Use | Code Reference | Behavior |
| --- | --- | --- | --- |
| `timeframe` | pipeline data window granularity | `src/tycherion/bootstrap/main.py` | passed into `ModelPipelineService(timeframe=...)` |
| `lookback_days` | historical lookback window | `src/tycherion/bootstrap/main.py` | passed into `ModelPipelineService(lookback_days=...)` |
| `trading.dry_run` | execution safety mode | `src/tycherion/bootstrap/main.py` | passed to `MT5Trader` |
| `trading.require_demo` | block non-demo account execution | `src/tycherion/bootstrap/main.py` | passed to `MT5Trader` |
| `trading.deviation_points` | order slippage tolerance | `src/tycherion/bootstrap/main.py` | passed to `MT5Trader` |
| `trading.volume_mode` | volume strategy (`min`/`fixed`) | `src/tycherion/application/services/order_planner.py` | drives `volume_from_weight(...)` |
| `trading.fixed_volume` | fixed order volume | `src/tycherion/application/services/order_planner.py` | used when `volume_mode=fixed` |
| `mt5.*` | terminal/session auth | `src/tycherion/bootstrap/main.py` | consumed by `_ensure_initialized(...)` |
| `application.run_mode.name` | run mode dispatch | `src/tycherion/bootstrap/main.py` | selects `run_live_multimodel(...)` |
| `application.playbook` | indicator selection context | `src/tycherion/bootstrap/main.py` | passed into `ModelPipelineService(playbook=...)` |
| `application.schedule.run_forever` | loop vs single-run | `src/tycherion/application/runmodes/live_multimodel.py` | controls while-loop behavior |
| `application.schedule.interval_seconds` | loop interval | `src/tycherion/application/runmodes/live_multimodel.py` | controls `sleep(...)` duration |
| `application.coverage.*` | symbol universe selection | `src/tycherion/application/services/coverage_selector.py` | resolves static/market_watch/pattern symbols |
| `application.models.pipeline` | pipeline stage list | `src/tycherion/application/pipeline/config.py` | normalized into `PipelineConfig` |
| `application.portfolio.allocator` | allocator plugin selection | `src/tycherion/application/runmodes/live_multimodel.py` | resolver key in `ALLOCATORS` |
| `application.portfolio.balancer` | balancer plugin selection | `src/tycherion/application/runmodes/live_multimodel.py` | resolver key in `BALANCERS` |
| `application.portfolio.threshold_weight` | rebalance sensitivity | `src/tycherion/application/runmodes/live_multimodel.py` | passed as `threshold` to balancer |
| `observability.*` | logs/traces/metrics sink config | `src/tycherion/bootstrap/main.py` | consumed by `_build_observability(...)` |

## Notes
- Canonical observability key is `observability`.
- Deprecated alias `telemetry` is accepted by the loader for backward compatibility.
- `risk.*` is currently a forward-compatible contract and not fully enforced in the live execution path.

## Links
- Next: [Architecture Overview](../architecture/overview.md)
- See also: [Canonical Config Paths ADR](../architecture/decisions/adr-0002-canonical-config-paths.md)
