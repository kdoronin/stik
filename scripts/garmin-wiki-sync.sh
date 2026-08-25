#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
WIKI_PATH="${WIKI_PATH:?Set WIKI_PATH to the owner LLM Wiki directory}"
FITNESS_TIMEZONE="${FITNESS_TIMEZONE:?Set FITNESS_TIMEZONE, for example Europe/Berlin}"
export WIKI_PATH FITNESS_TIMEZONE

exec "$HERMES_HOME/integrations/garmin-mcp/.venv/bin/python" \
  "$HERMES_HOME/integrations/garmin-mcp/garmin_sync.py" \
  --wiki "$WIKI_PATH"
