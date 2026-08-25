# Install the included read-only Strava MCP connector

## Result

After this procedure, an MCP client can read:

- connection status;
- athlete profile and zones;
- athlete totals;
- recent activities;
- activity details and laps;
- time-series streams for heart rate, pace, cadence, power, altitude, temperature, movement, grade, distance, and GPS.

The connector exposes no Strava write tools.

## Sources

- Included source: `./strava-mcp/`
- Official Strava setup guide: https://developers.strava.com/docs/getting-started/
- OAuth documentation: https://developers.strava.com/docs/authentication/
- API reference: https://developers.strava.com/docs/reference/
- API application page: https://www.strava.com/settings/api

There is no public upstream repository for this exact connector. Do not replace it with a similarly named package and claim it is the same implementation.

## Prerequisites

- Python 3.11 or newer; Python 3.12 is recommended.
- `uv`: https://docs.astral.sh/uv/
- A Strava subscription, because Strava currently requires one to create an API application.
- An MCP-compatible client. Hermes instructions are below.

## 1. Install

The shared installer copies the complete source to the owner-specific Hermes integration directory:

```bash
chmod 755 scripts/*.sh
./scripts/install-connectors.sh
STRAVA_DIR="${HERMES_HOME:-$HOME/.hermes}/integrations/strava-mcp"
uv run --project "$STRAVA_DIR" --group dev pytest -q "$STRAVA_DIR/tests"
```

Expected test properties include:

- only `read,activity:read_all,profile:read_all` OAuth scopes;
- OAuth `state` validation;
- owner-only credential file permissions;
- refresh-token rotation persistence;
- bounded pagination;
- Bearer authentication on API requests;
- no MCP write tools.

The package includes the same optional Strava → LLM Wiki backfill code as the reference installation (`strava-wiki-sync`, `wiki_sync.py`, and `scripts/strava-wiki-backfill.py`). It contains no owner paths, credentials, scheduled jobs, or activity records. Enable the backfill only after the owner provides a compatible `WIKI_PATH`; run it manually once before scheduling it.

## 2. Create the Strava API application

Open:

https://www.strava.com/settings/api

Create an application and set:

```text
Authorization Callback Domain: localhost
```

Do not paste the Client Secret into chat, a ticket, or an agent prompt.

## 3. Authenticate interactively

Run the installed command in a local terminal controlled by the human:

```bash
STRAVA_DIR="${HERMES_HOME:-$HOME/.hermes}/integrations/strava-mcp"
"$STRAVA_DIR/.venv/bin/strava-auth"
```

The command asks for the Client ID and Client Secret, opens the Strava consent page, and listens once on:

```text
http://localhost:8111/callback
```

Requested scopes:

```text
read,activity:read_all,profile:read_all
```

Tokens are stored in:

```text
~/.config/hermes-strava-mcp/config.json
```

Verify permissions:

```bash
stat -f '%Sp %N' ~/.config/hermes-strava-mcp ~/.config/hermes-strava-mcp/config.json 2>/dev/null \
  || stat -c '%A %n' ~/.config/hermes-strava-mcp ~/.config/hermes-strava-mcp/config.json
```

Required result:

```text
directory: drwx------
file:      -rw-------
```

## 4. Add to Hermes Agent

Resolve the installed executable:

```bash
STRAVA_MCP="${HERMES_HOME:-$HOME/.hermes}/integrations/strava-mcp/.venv/bin/strava-mcp"
test -x "$STRAVA_MCP"
hermes mcp add strava --command "$STRAVA_MCP"
hermes mcp test strava
```

Expected inventory: exactly eight tools.

```text
connection_status
athlete_profile
athlete_zones
athlete_stats
recent_activities
activity_details
activity_laps
activity_streams
```

Reload MCP in the active Hermes session or restart the client:

```text
/reload-mcp
```

If the client does not support hot reload, start a new session.

## 5. Live verification

A handshake is insufficient. Verify all of these with actual MCP calls:

1. `connection_status` returns `connected: true`, `mode: read-only`, and the expected scopes.
2. `athlete_profile` returns the authenticated athlete.
3. `recent_activities(per_page=3)` returns real activities.
4. `activity_details` succeeds for one returned activity ID.
5. `activity_laps` succeeds for the same ID.
6. `activity_streams` returns available streams for that activity. Missing power or cadence can be normal if the recording device did not capture them.

Do not print or log the contents of the credential file.

## 6. Other MCP clients

Use the absolute path to `strava-mcp/.venv/bin/strava-mcp` as a local `stdio` command. For example, the generic MCP shape is:

```json
{
  "mcpServers": {
    "strava": {
      "command": "/absolute/path/to/strava-mcp/.venv/bin/strava-mcp",
      "args": []
    }
  }
}
```

Client-specific configuration locations differ. Restart the client after changing its MCP configuration.

## Troubleshooting

### Port 8111 is busy

Find the local process using the port, stop it if safe, then rerun `uv run strava-auth`. Do not change the callback port in only one place; the Strava redirect URI and local listener must match.

### Private activities are missing

Reauthenticate and confirm Strava granted `activity:read_all`. The connector requests it, but the athlete must accept it.

### Token refresh fails later

Rerun `uv run strava-auth`. Never repair the config by pasting tokens into chat.

### Rate limits

Strava enforces per-application limits. Keep pagination bounded and avoid repeatedly downloading long history or high-frequency streams. See https://developers.strava.com/docs/rate-limits/.
