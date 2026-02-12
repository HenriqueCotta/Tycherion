# Secrets and Credential Handling

Audience: developers, operators, and CI maintainers.
Goal: prevent credential leaks and define mandatory secret handling rules.

## Expected Outcome

- Secrets stay out of git history and shared configs.
- Developers know safe local and CI secret patterns.

## Prerequisites

- `.env.example` is available locally.
- `.gitignore` includes `.env`.

## Policy

- Never commit `.env` or any secret-bearing config file.
- Keep secrets in local `.env` (developer machine) or CI secret store.
- Rotate credentials immediately after any suspected leak.

## Local Development

1. Create `.env` from template:

    ```powershell
    copy .env.example .env
    ```

2. Fill local values only:

   - `MT5_TERMINAL_PATH`
   - `MT5_SERVER`
   - `MT5_LOGIN`
   - `MT5_PASSWORD`

3. Keep `.env` out of commits (`.gitignore` includes `.env`).

## CI and Shared Environments

- Inject secrets as environment variables using CI secret management.
- Do not place secrets in repository YAML files.
- Restrict secret scope to the minimum required jobs.

## Validation Mode Safety Toggles

- Keep `trading.dry_run=true` during local and CI validation.
- Keep `trading.require_demo=true` unless a controlled production workflow is explicitly approved.

## Incident Response

If credentials are exposed in logs, dumps, or commits:

1. Rotate MT5 credentials immediately.
2. Remove exposed files from history if applicable.
3. Audit recent activity for unauthorized usage.
4. Document incident and preventive action.

## Rollback

- Restore credentials from a trusted secret source.
- Revert local config changes to baseline before revalidating runtime.
- Run one cycle in `dry_run` mode after secret changes.

## Links

- Next: [Quickstart](./quickstart.md)
- See also: [Configuration Reference](../reference/configuration.md)
