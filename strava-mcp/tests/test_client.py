from strava_mcp.client import StravaClient
from strava_mcp.core import ConfigStore


class FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, method, url, *, data=None, headers=None):
        self.calls.append((method, url, data, headers or {}))
        if url.endswith("/oauth/token"):
            return {
                "access_token": "fresh-access",
                "refresh_token": "fresh-refresh",
                "expires_at": 9999999999,
            }
        return {"ok": True}


def test_expired_token_is_refreshed_and_persisted(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.save(
        {
            "client_id": "123",
            "client_secret": "secret",
            "access_token": "expired",
            "refresh_token": "refresh",
            "expires_at": 1,
        }
    )
    transport = FakeTransport()
    client = StravaClient(store=store, transport=transport, now=lambda: 100)

    assert client.access_token() == "fresh-access"
    assert store.load()["refresh_token"] == "fresh-refresh"
    assert transport.calls[0][2]["grant_type"] == "refresh_token"


def test_api_get_uses_bearer_token(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.save(
        {
            "access_token": "valid-access",
            "refresh_token": "refresh",
            "expires_at": 9999999999,
        }
    )
    transport = FakeTransport()
    client = StravaClient(store=store, transport=transport, now=lambda: 100)

    assert client.get("/athlete") == {"ok": True}
    _, url, _, headers = transport.calls[0]
    assert url == "https://www.strava.com/api/v3/athlete"
    assert headers["Authorization"] == "Bearer valid-access"
