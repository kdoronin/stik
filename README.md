# Strava + Garmin MCP installation kit

This kit reproduces the fitness integration topology used by the reference Hermes installation while adapting paths, credentials, timezone, and Wiki location to the new owner.

## Included

| Component | Source and update policy |
|---|---|
| Strava MCP | Complete owner-neutral source in `strava-mcp/`; official Strava REST API and OAuth 2.0; eight read-only tools |
| Garmin MCP | Current `main` branch of https://github.com/Taxuspt/garmin_mcp at initial installation; later updates require an explicit owner request |
| Garmin Wiki sync | Read-only overlay in `garmin-overlay/`; configurable with `WIKI_PATH` and `FITNESS_TIMEZONE` |
| Strava Wiki backfill | Included in the Strava source and in `scripts/strava-wiki-backfill.py`; optional |
| Agent host | Hermes Agent with native MCP support, or another MCP-compatible client |

The archive contains no account credentials, OAuth application identifiers, tokens, cookies, activity records, or owner-specific paths.

## Start here

- [`INSTALL-FOR-AGENT.md`](INSTALL-FOR-AGENT.md) — complete autonomous-agent task and acceptance criteria.
- [`STRAVA-MCP.md`](STRAVA-MCP.md) — Strava authentication, tests, registration, and live checks.
- [`GARMIN-MCP.md`](GARMIN-MCP.md) — Garmin authentication, update behavior, capability profiles, and live checks.
- `scripts/install-connectors.sh` — installs the supplied Strava source and the current Garmin `main` branch into `${HERMES_HOME:-~/.hermes}/integrations/`.

## Capability parity

The reference installation exposes all Strava tools read-only. Its Garmin profile includes the read tools plus workout upload, scheduling, deletion, and unscheduling. Those Garmin operations alter the owner's account. An agent may reproduce that full profile only after the owner explicitly authorizes it; otherwise it must install the read-only profile.

## Optional Wiki synchronization

Wiki synchronization is separate from MCP access. Enable it only when the owner has an LLM Wiki compatible with the supplied writers and has provided:

- `WIKI_PATH` — the actual Wiki directory;
- `FITNESS_TIMEZONE` — an IANA timezone such as `Europe/Berlin`;
- authorization to create the documented scheduled jobs.

The installer must never assume another owner's username, home directory, timezone, Wiki schema, Telegram destination, or scheduler.

## Canonical links

- Hermes MCP documentation: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
- Model Context Protocol: https://modelcontextprotocol.io/
- Strava API: https://developers.strava.com/docs/reference/
- Strava OAuth: https://developers.strava.com/docs/authentication/
- Strava application settings: https://www.strava.com/settings/api
- Garmin MCP: https://github.com/Taxuspt/garmin_mcp
- Garmin MCP current branch: https://github.com/Taxuspt/garmin_mcp/tree/main
- Underlying Garmin client: https://github.com/cyberjunky/python-garminconnect

## Security boundary

Use local `stdio`. Credentials are entered only in a human-controlled terminal or browser and remain outside the archive and MCP configuration. Garmin is unofficial. The runtime uses the installed, verified revision and performs no automatic network or update check. After an explicit owner request, the guarded updater fetches current `main`, reruns safe tests, and restores the prior revision if validation fails.
