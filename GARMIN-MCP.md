# Install the Garmin MCP connector

## Source and runtime

- Repository: https://github.com/Taxuspt/garmin_mcp
- Branch policy: resolve current upstream `main` during initial installation; update later only after an explicit owner request
- Installation path: `${HERMES_HOME:-$HOME/.hermes}/integrations/garmin-mcp`
- Runtime wrapper: `run-garmin-mcp.sh` (starts the installed revision without network access)
- Transport: local `stdio`

The runtime wrapper performs no update check. Record the installed commit in verification output for diagnosis. To update, the owner must explicitly request it; only then run `update-garmin-mcp.sh --owner-approved`. The updater fetches `main`, runs the safe test set, and restores the previous revision if validation fails.

Garmin Connect access is unofficial and may break when private endpoints change.

## Capability profiles

### Read-only profile

```text
get_stats,get_daily_steps,get_steps_data,get_sleep_data,get_sleep_summary,get_training_readiness,get_morning_training_readiness,get_body_battery,get_hrv_data,get_stress_summary,get_respiration_summary,get_spo2_data,get_rhr_day,get_heart_rates_summary,get_activities_by_date,get_activity,get_training_status,get_weekly_intensity_minutes,get_workouts,get_workout_by_id,get_scheduled_workouts
```

### Reference-parity workout profile

The reference installation adds exactly:

```text
upload_workout,upload_workouts,schedule_workout,delete_workout,delete_workouts,unschedule_workout,unschedule_workouts
```

The current upstream inventory is 21 read-only tools or 28 tools with the authorized workout profile. Older configuration may still mention `get_profile`; current `main` does not register that tool, so it must not remain in the expected allowlist.

These tools alter the Garmin account. Enable them only after explicit owner authorization. Do not add nutrition, activity-editing, gear, course, challenge, or arbitrary mutation tools.

## Install or update

From the unpacked kit:

```bash
chmod 755 scripts/*.sh
./scripts/install-connectors.sh
```

Safe automated tests exclude live E2E tests because upstream E2E tests use saved Garmin tokens and can create, modify, or delete real account records:

```bash
GARMIN_DIR="${HERMES_HOME:-$HOME/.hermes}/integrations/garmin-mcp"
uv run --project "$GARMIN_DIR" pytest -q \
  "$GARMIN_DIR/tests/unit" \
  "$GARMIN_DIR/tests/integration" \
  "$GARMIN_DIR/tests/test_wiki_sync.py"
```

Never run the full upstream test suite against an owner's token directory unless the owner separately authorizes live account mutations.

## Authenticate

Run in a human-controlled terminal:

```bash
GARMIN_DIR="${HERMES_HOME:-$HOME/.hermes}/integrations/garmin-mcp"
"$GARMIN_DIR/.venv/bin/garmin-mcp-auth"
"$GARMIN_DIR/.venv/bin/garmin-mcp-auth" --verify
chmod 700 ~/.garminconnect
find ~/.garminconnect -type f -exec chmod 600 {} +
```

The owner enters email, password, and MFA locally. The agent must not request or print them.

## Register with Hermes

Choose one allowlist above. For exact reference capability, concatenate both lists after the owner authorizes account-changing workout tools.

```bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
GARMIN_COMMAND="$HERMES_HOME/integrations/garmin-mcp/run-garmin-mcp.sh"
GARMIN_TOOLS='<chosen comma-separated allowlist>'

hermes mcp add garmin \
  --command "$GARMIN_COMMAND" \
  --connect-timeout 60 \
  --env "GARMIN_ENABLED_TOOLS=$GARMIN_TOOLS"
hermes mcp configure garmin
hermes mcp test garmin
```

In Hermes, set `sampling.enabled: false` for this server and keep `tools.include` identical to `GARMIN_ENABLED_TOOLS`. Reload MCP or start a fresh session.

For another MCP client, use the absolute runtime-wrapper path as the local `stdio` command and pass only `GARMIN_ENABLED_TOOLS` in the environment.

## Verification

1. Record the installed revision with `git -C "$GARMIN_DIR" rev-parse HEAD`; startup must not contact GitHub or change it.
2. MCP initializes successfully.
3. Discovered tools equal the chosen allowlist exactly.
4. Read checks succeed for current stats, steps, sleep, recovery metrics where supported, recent activities, and one activity detail.
5. If full workout capability was authorized, verify only inventory at first. Do not upload, schedule, delete, or unschedule a real workout merely to prove installation.
6. Token paths are owner-only and token contents never enter logs or chat.

## Optional Garmin → LLM Wiki sync

The supplied `garmin-overlay/garmin_sync.py` performs read-only incremental snapshots. Set owner-specific values:

```bash
export WIKI_PATH='/absolute/path/to/wiki'
export FITNESS_TIMEZONE='Europe/Berlin'
./scripts/garmin-wiki-sync.sh
```

Run it once and inspect files before scheduling it. For Hermes cron, copy `scripts/garmin-wiki-sync.sh` under `~/.hermes/scripts/`, preserve the two environment variables in the script or scheduler environment, then create a script-only job. The reference cadence is every 30 minutes during waking hours; adapt it to the owner's timezone and provider load.

## Failure handling

- Authentication failure: rerun `garmin-mcp-auth` locally.
- Unexpected tools: disable the server and repair both allowlists before continuing.
- Do not check for or install updates during ordinary startup.
- When the owner explicitly requests an update, run `"$GARMIN_DIR/update-garmin-mcp.sh" --owner-approved`. If validation fails, confirm that the script restored the previous revision and report the upstream regression.
