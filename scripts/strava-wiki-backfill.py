#!/usr/bin/env python3
"""Silent recurring wrapper for the optional Strava -> LLM Wiki backfill."""

import json
import os
import subprocess
from pathlib import Path

wiki_value = os.environ.get("WIKI_PATH")
if not wiki_value:
    raise SystemExit("Set WIKI_PATH to the owner's LLM Wiki directory")
wiki = Path(wiki_value).expanduser()
state_path = wiki / "_meta/state/strava-history-sync.json"
hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
command = hermes_home / "integrations/strava-mcp/.venv/bin/strava-wiki-sync"

if state_path.exists():
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("completed"):
        raise SystemExit(0)

env = os.environ.copy()
env.setdefault("STRAVA_WIKI_BATCH_SIZE", "20")
env.setdefault("STRAVA_WIKI_REQUEST_DELAY", "2")
result = subprocess.run([str(command)], env=env, text=True, capture_output=True)
if result.returncode:
    print((result.stderr or result.stdout or "Strava Wiki backfill failed").strip())
    raise SystemExit(result.returncode)
if result.stdout.strip():
    print(result.stdout.strip())
