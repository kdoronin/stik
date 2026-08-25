from strava_mcp.service import StravaService


class FakeClient:
    def __init__(self):
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        return {"path": path, "params": params}


def test_recent_activities_caps_page_size_at_strava_limit():
    client = FakeClient()
    service = StravaService(client)

    service.recent_activities(per_page=500, page=2)

    assert client.calls == [("/athlete/activities", {"page": 2, "per_page": 100})]


def test_activity_streams_requests_compact_keyed_streams():
    client = FakeClient()
    service = StravaService(client)

    service.activity_streams(42, ["time", "heartrate", "watts"])

    assert client.calls == [
        (
            "/activities/42/streams",
            {"keys": "time,heartrate,watts", "key_by_type": "true"},
        )
    ]
