# MT5 Connectivity and Auth Runbook

Audience: operators and on-call engineers.
Goal: restore market-data and trading connectivity when MT5 terminal/session access fails.

## Symptoms

- No market data for all symbols.
- MT5 initialize or login failures at startup.
- Coverage symbols resolve but data fetch returns empty consistently.

## Checks

1. Confirm credentials and terminal path source:

   - `MT5_TERMINAL_PATH`
   - `MT5_SERVER`
   - `MT5_LOGIN`
   - `MT5_PASSWORD`

2. Confirm terminal is installed and reachable on host.
3. Confirm account can authenticate in MT5 terminal manually.
4. Confirm symbols are visible/selectable in Market Watch.

## Mitigation

- Re-apply known-good local `.env` and restart one-cycle run.
- Switch to demo account credentials if production credentials are unavailable.
- Reduce symbol universe to a small static set while restoring connectivity.

## Rollback

1. Set `trading.dry_run=true`.
2. Set `application.schedule.run_forever=false`.
3. Run a single-cycle validation after connectivity changes.

## Escalation

- Escalate if initialization/login still fails after one credential and terminal-path rollback.
- Include MT5 error output, config source, and host details.

## Code Investigation Pointers

- `src/tycherion/bootstrap/main.py` (`_ensure_initialized`)
- `src/tycherion/adapters/mt5/market_data_mt5.py`
- `src/tycherion/adapters/mt5/universe_mt5.py`

## Links

- Next: [Order Execution Failures Runbook](./order-execution-failures.md)
- See also: [Troubleshooting](../guides/troubleshooting.md)
