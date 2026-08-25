# Autonomous-agent task: reproduce the fitness MCP integration

## Mission

Install and verify the Strava and Garmin integration supplied by this kit for the current machine owner. Reproduce the reference topology without copying its username, paths, credentials, Wiki, timezone, Telegram destination, or historical data.

```text
Strava official API -> bundled local read-only MCP -> MCP client
Garmin Connect private API -> current upstream main -> allowlisted local MCP -> MCP client
Optional: both connectors -> owner-approved local LLM Wiki synchronization
```

Read `README.md`, `STRAVA-MCP.md`, and `GARMIN-MCP.md` before acting.

## Non-negotiable rules

1. Never request passwords, MFA codes, OAuth secrets, access tokens, refresh tokens, cookies, or token-file contents in chat.
2. Use a human-controlled local terminal/browser for authentication.
3. Use local `stdio`; do not expose an unauthenticated HTTP listener.
4. Keep Strava at exactly eight read-only tools and scopes `read,activity:read_all,profile:read_all`.
5. Ask the owner before enabling Garmin workout upload, schedule, delete, or unschedule tools. Without explicit authorization, use the read-only profile.
6. Resolve Garmin's current upstream `main` during initial installation. Afterward, never check for or install updates automatically; update only after an explicit owner request.
7. Do not run Garmin's complete upstream test suite with real tokens present. Its E2E tests can mutate the account. Run only the safe test paths listed in `GARMIN-MCP.md`.
8. Do not infer success from process startup or tool discovery. Perform narrow live read calls.
9. Wiki synchronization is optional and requires an actual compatible Wiki path and IANA timezone from the owner.
10. Do not overwrite an existing working installation. Back up MCP configuration, inspect existing entries, and stop on tracked local changes.

## Phase A — discover the owner environment

Record OS, home directory, Python, `uv`, `git`, MCP client, existing `strava`/`garmin` entries, and `HERMES_HOME`. Ask only for decisions that tools cannot discover:

- read-only Garmin or reference-parity workout management;
- MCP access only or optional Wiki synchronization;
- if Wiki sync is wanted: `WIKI_PATH`, `FITNESS_TIMEZONE`, cadence, and scheduler destination.

Do not inspect credential contents.

## Phase B — install source

Run:

```bash
chmod 755 scripts/*.sh
./scripts/install-connectors.sh
```

This copies the complete bundled Strava wrapper, resolves Garmin `origin/main` for a new installation, creates isolated Python 3.12 environments, installs the Garmin Wiki overlay, and prints executable paths plus the resolved Garmin commit. If Garmin is already installed, the installer refuses to update it unless the owner explicitly requested the update and the agent passes `--owner-approved-update`.

## Phase C — safe source verification

Strava:

```bash
STRAVA_DIR="${HERMES_HOME:-$HOME/.hermes}/integrations/strava-mcp"
uv run --project "$STRAVA_DIR" --group dev pytest -q "$STRAVA_DIR/tests"
STRAVA_MCP_COMMAND="$STRAVA_DIR/.venv/bin/strava-mcp" \
  uv run --project "$STRAVA_DIR" python "$STRAVA_DIR/scripts/smoke_mcp.py"
```

Garmin:

```bash
GARMIN_DIR="${HERMES_HOME:-$HOME/.hermes}/integrations/garmin-mcp"
uv run --project "$GARMIN_DIR" pytest -q \
  "$GARMIN_DIR/tests/unit" \
  "$GARMIN_DIR/tests/integration" \
  "$GARMIN_DIR/tests/test_wiki_sync.py"
```

Stop on failures. Never broaden Garmin tests to `tests/e2e` during installation.

## Phase D — authenticate and register

Follow the authentication commands in each connector document. Register absolute local `stdio` commands.

For Garmin:

- runtime command: `$HERMES_HOME/integrations/garmin-mcp/run-garmin-mcp.sh`;
- server-side `GARMIN_ENABLED_TOOLS`: exactly the owner-approved profile;
- Hermes `tools.include`: identical to the server-side allowlist;
- Hermes sampling: disabled;
- ordinary startup performs no Git or package update check.

For Strava:

- runtime command: `$HERMES_HOME/integrations/strava-mcp/.venv/bin/strava-mcp`;
- no write scopes;
- exactly eight discovered tools.

## Phase E — live verification

Strava: connection status, profile, recent activities, one detail, laps, and streams.

Garmin: current stats, steps, latest sleep, available Body Battery/HRV/readiness, recent activities, and one detail.

Inventory verification is sufficient for authorized Garmin write tools. Do not create or delete a real workout as an installation test.

For Hermes, run:

```bash
hermes mcp test strava
hermes mcp test garmin
hermes mcp list
```

Reload MCP or start a fresh session, then repeat one live read from each connector.

## Phase F — optional Wiki synchronization

Only when requested:

1. Validate that `WIKI_PATH` exists and its schema is compatible with the supplied writers.
2. Run each synchronization script once manually with the owner's environment.
3. Verify actual state, raw snapshots, generated metric pages, permissions, and absence of secrets.
4. Schedule only after the manual run succeeds.
5. Strava backfill stops silently when its state says `completed`; Garmin sync remains recurring.

Do not copy the reference owner's cron destinations or absolute paths.

## Acceptance criteria

- [ ] Bundled Strava source is installed, including Wiki sync and its tests.
- [ ] All Strava tests pass and exactly eight read-only tools are exposed.
- [ ] Strava OAuth is connected with the required read scopes and returns real records.
- [ ] A new Garmin installation was resolved from current upstream `main`; the installed commit is recorded as evidence. Existing installations were not updated without explicit owner approval.
- [ ] Safe Garmin unit/integration/overlay tests pass; live mutation tests were not run.
- [ ] Garmin tokens have owner-only permissions.
- [ ] Garmin tool inventory exactly matches the owner-approved profile.
- [ ] Hermes sampling is disabled for Garmin.
- [ ] Both servers use local `stdio` and survive a fresh client session.
- [ ] No secret appears in chat, logs, archive, or MCP configuration.
- [ ] Optional Wiki jobs, if requested, use the new owner's path, timezone, and destination and have completed one verified manual run.

## Final report

Report per connector: source, update policy, observed revision/version, install and executable paths, transport, authentication state, permission checks, safe-test output, discovered tools, live read calls, and remaining action. Distinguish `PASS`, `PARTIAL`, and `BLOCKED` with the exact reason.
