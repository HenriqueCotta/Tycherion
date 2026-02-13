# Quickstart

Audience: new developers.
Goal: run Tycherion locally in demo mode and validate one full cycle with observability enabled.

## Expected Outcome

- Local environment is configured.
- A single-cycle run succeeds with `dry_run=true`.
- Console observability signals are visible, with optional OTLP export.

## Prerequisites

- Python 3.10+.
- MetaTrader 5 installed on the same machine.
- Demo account credentials.

## Security Notes (Mandatory)

- Never commit `.env` with credentials.
- Keep secrets only in local `.env` or CI secret store.
- If credentials leak, rotate immediately.

## Steps

1. Create a virtual environment and install dependencies.

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\activate
    pip install -e .
    ```

2. Create local config.

    ```powershell
    copy configs\demo.yaml configs\local.yaml
    ```

    Optional local env template:

    ```powershell
    copy .env.example .env
    ```

3. Configure credentials in environment variables or local `.env`.

   - `MT5_TERMINAL_PATH`, `MT5_SERVER`, `MT5_LOGIN`, `MT5_PASSWORD`
4. Optional observability overrides.
   - `TYCHERION_OTLP_*`
   - `TYCHERION_CONSOLE_ENABLED`, `TYCHERION_CONSOLE_MIN_LEVEL`, `TYCHERION_CONSOLE_CHANNELS`

5. Run one cycle.

    ```powershell
    python -c "from tycherion.bootstrap.main import run_app; run_app('configs/local.yaml')"
    ```

## Validation

- MT5: no real orders when `dry_run=true`.
- Logs: operational logs appear in console when `console_enabled=true`.
- Pipeline: no startup/config exceptions.

## Rollback

- Set `trading.dry_run=true` and `trading.require_demo=true`.
- Set `application.schedule.run_forever=false` while validating changes.
- Revert to `configs/demo.yaml` baseline if custom config fails.

## Links

- Next: [Operations Guide](./operations.md)
- See also: [Configuration Reference](../reference/configuration.md)
- See also: [Tutorial: First End-to-End Cycle](./tutorial-first-end-to-end-cycle.md)
- See also: [Trading and MT5 Fundamentals](../concepts/trading-mt5-fundamentals.md)
