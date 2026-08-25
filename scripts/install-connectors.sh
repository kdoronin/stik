#!/usr/bin/env bash
set -euo pipefail

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
INTEGRATIONS_DIR="${HERMES_INTEGRATIONS_DIR:-$HERMES_HOME/integrations}"
STRAVA_DIR="$INTEGRATIONS_DIR/strava-mcp"
GARMIN_DIR="$INTEGRATIONS_DIR/garmin-mcp"
GARMIN_REPO="https://github.com/Taxuspt/garmin_mcp.git"

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }

if [[ -d "$STRAVA_DIR" || -d "$GARMIN_DIR/.git" ]]; then
  if [[ "${1:-}" != "--owner-approved-update" ]]; then
    echo "A fitness connector is already installed. Refusing to update it without an explicit owner request." >&2
    echo "After approval, rerun with: $0 --owner-approved-update" >&2
    exit 2
  fi
fi

mkdir -p "$INTEGRATIONS_DIR"

# Install the complete Strava source supplied by the kit. Runtime state and tokens
# are deliberately outside this source tree and are not copied.
mkdir -p "$STRAVA_DIR"
python3 - "$KIT_ROOT/strava-mcp" "$STRAVA_DIR" <<'PY'
from pathlib import Path
import shutil, sys
src, dst = map(Path, sys.argv[1:])
for child in src.iterdir():
    target = dst / child.name
    if child.is_dir():
        shutil.copytree(child, target, dirs_exist_ok=True)
    else:
        shutil.copy2(child, target)
PY
uv sync --project "$STRAVA_DIR" --python 3.12 --group dev

# Resolve the current upstream main branch; no fixed commit is stored in the kit.
if [[ ! -d "$GARMIN_DIR/.git" ]]; then
  if [[ -e "$GARMIN_DIR" ]] && [[ -n "$(find "$GARMIN_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    echo "Refusing to replace non-Git directory: $GARMIN_DIR" >&2
    exit 1
  fi
  git clone --filter=blob:none --branch main "$GARMIN_REPO" "$GARMIN_DIR"
else
  if [[ "${1:-}" != "--owner-approved-update" ]]; then
    echo "Garmin MCP is already installed. Refusing to update it without an explicit owner request." >&2
    echo "After approval, rerun with: $0 --owner-approved-update" >&2
    exit 2
  fi
  git -C "$GARMIN_DIR" remote set-url origin "$GARMIN_REPO"
  if ! git -C "$GARMIN_DIR" diff --quiet || ! git -C "$GARMIN_DIR" diff --cached --quiet; then
    echo "Tracked local changes in $GARMIN_DIR; refusing to update." >&2
    exit 1
  fi
  git -C "$GARMIN_DIR" fetch origin main
  git -C "$GARMIN_DIR" checkout --detach origin/main
fi

# Add the owner-neutral, read-only Wiki synchronization overlay.
cp "$KIT_ROOT/garmin-overlay/garmin_sync.py" "$GARMIN_DIR/garmin_sync.py"
cp "$KIT_ROOT/garmin-overlay/tests/test_wiki_sync.py" "$GARMIN_DIR/tests/test_wiki_sync.py"
cp "$KIT_ROOT/scripts/run-garmin-mcp.sh" "$GARMIN_DIR/run-garmin-mcp.sh"
cp "$KIT_ROOT/scripts/update-garmin-mcp.sh" "$GARMIN_DIR/update-garmin-mcp.sh"
chmod 755 "$GARMIN_DIR/run-garmin-mcp.sh" "$GARMIN_DIR/update-garmin-mcp.sh"
uv sync --project "$GARMIN_DIR" --python 3.12

printf '%s\n' \
  "Installed Strava: $STRAVA_DIR/.venv/bin/strava-mcp" \
  "Installed Garmin: $GARMIN_DIR/.venv/bin/garmin-mcp" \
  "Garmin runtime wrapper: $GARMIN_DIR/run-garmin-mcp.sh" \
  "Resolved Garmin commit: $(git -C "$GARMIN_DIR" rev-parse HEAD)"
