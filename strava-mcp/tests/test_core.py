from pathlib import Path
from urllib.parse import parse_qs, urlparse

from strava_mcp.core import ConfigStore, build_authorization_url, merge_token_response


def test_authorization_url_requests_read_only_coaching_scopes():
    url = build_authorization_url("123", "http://localhost:8111/callback", state="nonce")
    query = parse_qs(urlparse(url).query)

    assert query["scope"] == ["read,activity:read_all,profile:read_all"]
    assert "write" not in query["scope"][0]
    assert query["state"] == ["nonce"]


def test_config_store_writes_owner_only_file(tmp_path: Path):
    path = tmp_path / "nested" / "config.json"
    ConfigStore(path).save({"access_token": "secret"})

    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert ConfigStore(path).load() == {"access_token": "secret"}


def test_merge_token_response_preserves_rotated_refresh_token():
    old = {"refresh_token": "old", "client_secret": "app-secret"}
    response = {"access_token": "new-access", "expires_at": 123, "refresh_token": "new-refresh"}

    merged = merge_token_response(old, response)

    assert merged["refresh_token"] == "new-refresh"
    assert merged["client_secret"] == "app-secret"


def test_merge_token_response_keeps_old_refresh_token_when_omitted():
    old = {"refresh_token": "old", "client_secret": "app-secret"}
    response = {"access_token": "new-access", "expires_at": 123}

    merged = merge_token_response(old, response)

    assert merged["refresh_token"] == "old"
