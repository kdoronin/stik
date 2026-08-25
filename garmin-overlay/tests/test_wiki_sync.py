from datetime import datetime
from zoneinfo import ZoneInfo

from garmin_sync import curated, sleep_summary, sync_once


class FakeGarmin:
    def get_stats(self, date):
        return {
            "calendarDate": date,
            "totalSteps": 12345,
            "dailyStepGoal": 18000,
            "bodyBatteryMostRecentValue": 62,
            "restingHeartRate": 52,
        }

    def get_body_battery(self, start, end):
        return [{"date": start, "charged": 50, "drained": 20}]

    def get_activities_by_date(self, start, end):
        return [{"activityId": 7, "activityName": "Run", "activityType": {"typeKey": "running"}}]

    def get_sleep_data(self, date):
        return {
            "dailySleepDTO": {
                "sleepTimeSeconds": 25200,
                "sleepScores": {"overall": {"value": 82}},
            }
        }

    def get_hrv_data(self, date):
        return {"hrvSummary": {"lastNightAvg": 44, "status": "BALANCED"}}

    def get_training_readiness(self, date):
        return [{"score": 71, "level": "HIGH"}]


def test_summary_extractors():
    assert sleep_summary(FakeGarmin().get_sleep_data("2026-08-08"))["sleep_score"] == 82
    assert curated({"data": {"stats": {"totalSteps": 10}}, "errors": {}})["steps"] == 10


def test_sync_writes_live_and_immutable_boundaries(tmp_path):
    morning = datetime(2026, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC"))
    summary = sync_once(FakeGarmin(), tmp_path, morning)
    assert summary["steps"] == 12345
    assert (tmp_path / "_meta/state/garmin-live.json").exists()
    assert (tmp_path / "metrics/garmin-current.md").exists()
    assert (tmp_path / "raw/garmin/daily/2026-08-08/morning.json").exists()
    assert not (tmp_path / "raw/garmin/daily/2026-08-08/final.json").exists()

    first_morning = (tmp_path / "raw/garmin/daily/2026-08-08/morning.json").read_bytes()
    sync_once(FakeGarmin(), tmp_path, morning.replace(hour=9))
    assert (tmp_path / "raw/garmin/daily/2026-08-08/morning.json").read_bytes() == first_morning

    sync_once(FakeGarmin(), tmp_path, morning.replace(hour=23))
    assert (tmp_path / "raw/garmin/daily/2026-08-08/final.json").exists()
