from strava_mcp.auth import complete_authorization
from strava_mcp.core import ConfigStore


def test_complete_authorization_stores_app_credentials_and_tokens(tmp_path):
    calls = []

    def transport(method, url, *, data=None, headers=None):
        calls.append((method, url, data))
        return {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": 9999999999,
            "athlete": {"id": 7, "firstname": "Test"},
        }

    store = ConfigStore(tmp_path / "config.json")
    athlete = complete_authorization(
        store=store,
        client_id="123",
        client_secret="secret",
        code="one-time-code",
        transport=transport,
    )

    saved = store.load()
    assert athlete["id"] == 7
    assert saved["client_id"] == "123"
    assert saved["client_secret"] == "secret"
    assert saved["refresh_token"] == "refresh"
    assert calls[0][2]["grant_type"] == "authorization_code"
