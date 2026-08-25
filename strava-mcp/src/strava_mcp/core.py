"""Core helpers for the local Strava connector."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode

AUTH_URL = "https://www.strava.com/oauth/authorize"
READ_ONLY_SCOPES = "read,activity:read_all,profile:read_all"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "hermes-strava-mcp" / "config.json"


class ConfigStore:
    def __init__(self, path: Path | str = DEFAULT_CONFIG_PATH):
        self.path = Path(path).expanduser()

    def load(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}

    def save(self, config: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(dict(config), indent=2) + "\n", encoding="utf-8")
        os.chmod(temp, 0o600)
        temp.replace(self.path)
        os.chmod(self.path, 0o600)


def build_authorization_url(client_id: str, redirect_uri: str, *, state: str) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "approval_prompt": "force",
            "scope": READ_ONLY_SCOPES,
            "state": state,
        }
    )
    return f"{AUTH_URL}?{query}"


def merge_token_response(existing: Mapping[str, Any], response: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    merged.update(response)
    if not response.get("refresh_token") and existing.get("refresh_token"):
        merged["refresh_token"] = existing["refresh_token"]
    return merged
