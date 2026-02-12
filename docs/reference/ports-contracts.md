# Ports Contracts

Audience: adapter authors and runtime maintainers.
Goal: define what each port guarantees, what callers assume, and how failures should surface.

## Contract Table
| Port | Operations | Caller Expectations | Adapter Obligations | Source |
| --- | --- | --- | --- | --- |
| `MarketDataPort` | `get_bars(symbol, timeframe, start, end)` | Returns a `pandas.DataFrame`; may be empty. Caller handles empty data by dropping non-held symbols. | Raise exceptions for hard failures; do not silently return corrupt structures. | `src/tycherion/ports/market_data.py`, `src/tycherion/application/pipeline/service.py` |
| `TradingPort` | `market_buy`, `market_sell` | Returns `TradeResult(ok, retcode, order, message)`; caller logs every execution result. | Map broker result into `TradeResult` consistently; keep `message` actionable. | `src/tycherion/ports/trading.py`, `src/tycherion/application/runmodes/live_multimodel.py` |
| `AccountPort` | `is_demo`, `balance`, `equity`, `positions` | `equity` and `positions` build `PortfolioSnapshot`; invalid values affect weight math. | Return numeric values and coherent positions list for the same account snapshot. | `src/tycherion/ports/account.py`, `src/tycherion/application/runmodes/live_multimodel.py` |
| `UniversePort` | `visible_symbols`, `by_pattern` | Coverage selector builds the symbol universe from this contract. | Return stable symbol identifiers compatible with broker adapters. | `src/tycherion/ports/universe.py`, `src/tycherion/application/services/coverage_selector.py` |
| `ObservabilityPort` | traces, logs, metrics providers | Application and domain-adjacent services emit events through ports only. | Provide no-op-safe behavior or concrete OTel export; do not break core logic. | `src/tycherion/ports/observability/`, `src/tycherion/bootstrap/main.py` |

## Port Invariants
- Port interfaces are infrastructure-agnostic. Domain and application layers do not import external SDK APIs directly.
- Adapter errors should be explicit (`raise`/error result), then logged through observability.
- Ports must remain backward compatible unless an ADR defines a breaking migration.

## Copy/Paste Contract Sanity Check
Use this to confirm plugin discovery and core runtime contracts are loadable:
```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from tycherion.application.plugins.registry import auto_discover, MODELS, ALLOCATORS, BALANCERS; from tycherion.adapters.observability.noop.noop_observability import NoopObservability; auto_discover(observability=NoopObservability()); print('models=', sorted(MODELS.keys())); print('allocators=', sorted(ALLOCATORS.keys())); print('balancers=', sorted(BALANCERS.keys()))"
```
Expected shape:
- `models` includes `mean_reversion` and `trend_following`.
- `allocators` includes `proportional`.
- `balancers` includes `threshold`.

## Links
- Next: [Execution Contract](./execution-contract.md)
- See also: [Architecture Overview](../architecture/overview.md)
