#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" != "--owner-approved" ]]; then
  echo "Refusing to update Garmin MCP without an explicit owner request." >&2
  echo "After approval, run: $0 --owner-approved" >&2
  exit 2
fi

if ! git -C "$ROOT" diff --quiet || ! git -C "$ROOT" diff --cached --quiet; then
  echo "Tracked local changes exist; refusing to update." >&2
  exit 1
fi

old="$(git -C "$ROOT" rev-parse HEAD)"
git -C "$ROOT" fetch origin main
latest="$(git -C "$ROOT" rev-parse origin/main)"
if [[ "$old" == "$latest" ]]; then
  echo "Garmin MCP is already at the current upstream main revision: $old"
  exit 0
fi

git -C "$ROOT" checkout --detach "$latest"
if uv sync --project "$ROOT" --python 3.12 && \
   uv run --project "$ROOT" pytest -q \
     "$ROOT/tests/unit" \
     "$ROOT/tests/integration" \
     "$ROOT/tests/test_wiki_sync.py"; then
  echo "Garmin MCP updated: $old -> $latest"
  exit 0
fi

echo "Update validation failed; restoring $old" >&2
git -C "$ROOT" checkout --detach "$old"
uv sync --project "$ROOT" --python 3.12
exit 1
