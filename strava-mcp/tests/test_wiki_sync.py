import json
from pathlib import Path

from strava_mcp.wiki_sync import SyncSettings, sync_once


class FakeClient:
    def __init__(self, list_payload, details):
        self.list_payload = list_payload
        self.details = details
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == "/athlete/activities":
            return self.list_payload
        activity_id = int(path.split("/")[2])
        return self.details[activity_id]


def make_wiki(root: Path):
    (root / "areas").mkdir(parents=True)
    (root / "metrics").mkdir()
    (root / "source-notes").mkdir()
    (root / "raw").mkdir()
    (root / "_meta" / "state").mkdir(parents=True)
    (root / "index.md").write_text(
        "# Wiki Index\n\n> Last updated: 2026-01-01 | Total content pages: 1\n\n"
        "## Core Areas\n\n- [[sport-and-physical-practice]] — Sport.\n\n"
        "## Metrics\n\n## Source Notes\n",
        encoding="utf-8",
    )
    (root / "log.md").write_text("# Wiki Log\n", encoding="utf-8")
    (root / "areas" / "sport-and-physical-practice.md").write_text("placeholder", encoding="utf-8")


def test_sync_once_fetches_details_writes_raw_and_updates_wiki(tmp_path):
    make_wiki(tmp_path)
    summaries = [
        {"id": 2, "start_date": "2025-01-02T10:00:00Z"},
        {"id": 1, "start_date": "2024-12-31T10:00:00Z"},
    ]
    details = {
        2: {
            "id": 2,
            "name": "Run",
            "type": "Run",
            "start_date": "2025-01-02T10:00:00Z",
            "start_date_local": "2025-01-02T13:00:00Z",
            "distance": 10000,
            "moving_time": 3600,
            "total_elevation_gain": 120,
            "average_heartrate": 150,
            "max_heartrate": 175,
        },
        1: {
            "id": 1,
            "name": "Ride",
            "type": "Ride",
            "start_date": "2024-12-31T10:00:00Z",
            "start_date_local": "2024-12-31T13:00:00Z",
            "distance": 20000,
            "moving_time": 4000,
            "total_elevation_gain": 200,
        },
    }
    client = FakeClient(summaries, details)

    result = sync_once(
        client,
        SyncSettings(wiki=tmp_path, batch_size=2, request_delay=0),
        today="2026-07-18",
    )

    assert result.imported == 2
    assert result.completed is False
    assert len(client.calls) == 3
    assert json.loads((tmp_path / "raw/strava/activities/2.json").read_text())["name"] == "Run"
    assert "| 2025-01-02 | Run | Run | 10.00 | 1:00:00 |" in (
        tmp_path / "metrics/strava-activities-2025.md"
    ).read_text()
    assert (tmp_path / "metrics/strava-activities-2024.md").exists()
    assert "[[metrics/strava-training-history" in (tmp_path / "index.md").read_text()
    state = json.loads((tmp_path / "_meta/state/strava-history-sync.json").read_text())
    assert state["before"] == 1735639200
    assert state["imported"] == 2


def test_empty_batch_marks_backfill_complete(tmp_path):
    make_wiki(tmp_path)
    client = FakeClient([], {})

    result = sync_once(
        client,
        SyncSettings(wiki=tmp_path, batch_size=5, request_delay=0),
        today="2026-07-18",
    )

    assert result.completed is True
    state = json.loads((tmp_path / "_meta/state/strava-history-sync.json").read_text())
    assert state["completed"] is True
    assert "Backfill complete" in (tmp_path / "metrics/strava-training-history.md").read_text()
