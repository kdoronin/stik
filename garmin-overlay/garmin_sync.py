#!/usr/bin/env python3
"""Read-only Garmin Connect sync into the local LLM Wiki.

The script stores a mutable live checkpoint, one immutable morning snapshot once
sleep is available, and one immutable final snapshot after 23:00 the configured local timezone.
It never calls Garmin write endpoints.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from garminconnect import Garmin  # type: ignore[import-not-found]

LOCAL_ZONE = ZoneInfo(os.environ.get("FITNESS_TIMEZONE", "UTC"))
DEFAULT_WIKI = Path(os.environ.get("WIKI_PATH", str(Path.home() / "wiki")))
DEFAULT_TOKENS = Path.home() / ".garminconnect"


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def call_endpoint(name: str, fn: Callable[[], Any], data: dict, errors: dict) -> None:
    try:
        data[name] = fn()
    except Exception as exc:  # keep partial snapshots and endpoint provenance
        errors[name] = f"{type(exc).__name__}: {exc}"


def sleep_summary(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    daily = payload.get("dailySleepDTO") or {}
    score = ((daily.get("sleepScores") or {}).get("overall") or {})
    spo2 = payload.get("wellnessSpO2SleepSummaryDTO") or {}
    return {
        key: value
        for key, value in {
            "sleep_seconds": daily.get("sleepTimeSeconds"),
            "sleep_start_gmt": daily.get("sleepStartTimestampGMT"),
            "sleep_end_gmt": daily.get("sleepEndTimestampGMT"),
            "sleep_score": score.get("value"),
            "sleep_score_qualifier": score.get("qualifierKey"),
            "deep_sleep_seconds": daily.get("deepSleepSeconds"),
            "light_sleep_seconds": daily.get("lightSleepSeconds"),
            "rem_sleep_seconds": daily.get("remSleepSeconds"),
            "awake_seconds": daily.get("awakeSleepSeconds"),
            "resting_heart_rate_bpm": daily.get("restingHeartRate"),
            "avg_sleep_stress": daily.get("avgSleepStress"),
            "avg_spo2_percent": spo2.get("averageSpo2"),
            "lowest_spo2_percent": spo2.get("lowestSpo2"),
        }.items()
        if value is not None
    }


def hrv_summary(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    summary = payload.get("hrvSummary") or {}
    baseline = summary.get("baseline") or {}
    return {
        key: value
        for key, value in {
            "last_night_avg_hrv_ms": summary.get("lastNightAvg"),
            "last_night_5min_high_hrv_ms": summary.get("lastNight5MinHigh"),
            "weekly_avg_hrv_ms": summary.get("weeklyAvg"),
            "status": summary.get("status"),
            "baseline_balanced_low_ms": baseline.get("balancedLow"),
            "baseline_balanced_upper_ms": baseline.get("balancedUpper"),
        }.items()
        if value is not None
    }


def latest_readiness(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list) or not payload:
        return {}
    item = payload[-1] if isinstance(payload[-1], dict) else {}
    return {
        key: value
        for key, value in {
            "score": item.get("score"),
            "level": item.get("level"),
            "feedback": item.get("feedbackShort"),
            "sleep_score": item.get("sleepScore"),
            "acute_load": item.get("acuteLoad"),
            "hrv_weekly_avg": item.get("hrvWeeklyAverage"),
            "timestamp_local": item.get("timestampLocal"),
        }.items()
        if value is not None
    }


def latest_activity(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list) or not payload:
        return {}
    item = payload[0] if isinstance(payload[0], dict) else {}
    activity_type = item.get("activityType") or {}
    return {
        key: value
        for key, value in {
            "activity_id": item.get("activityId"),
            "name": item.get("activityName"),
            "type": activity_type.get("typeKey") if isinstance(activity_type, dict) else None,
            "start_local": item.get("startTimeLocal"),
            "duration_seconds": item.get("duration"),
            "distance_meters": item.get("distance"),
            "average_hr_bpm": item.get("averageHR"),
            "max_hr_bpm": item.get("maxHR"),
        }.items()
        if value is not None
    }


def curated(snapshot: dict[str, Any]) -> dict[str, Any]:
    raw_data = snapshot.get("data")
    data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
    raw_stats = data.get("stats")
    stats: dict[str, Any] = raw_stats if isinstance(raw_stats, dict) else {}
    body_battery = data.get("body_battery")
    current_bb = stats.get("bodyBatteryMostRecentValue")
    if current_bb is None and isinstance(body_battery, list) and body_battery:
        day = body_battery[-1] if isinstance(body_battery[-1], dict) else {}
        feedback = day.get("bodyBatteryDynamicFeedbackEvent") or {}
        current_bb = feedback.get("bodyBatteryLevel")
    return {
        "observed_at": snapshot.get("observed_at"),
        "date": snapshot.get("date"),
        "provider_last_sync_gmt": stats.get("lastSyncTimestampGMT"),
        "provider_wellness_end_local": stats.get("wellnessEndTimeLocal"),
        "steps": stats.get("totalSteps"),
        "step_goal": stats.get("dailyStepGoal"),
        "body_battery_current": current_bb,
        "body_battery_charged": stats.get("bodyBatteryChargedValue"),
        "body_battery_drained": stats.get("bodyBatteryDrainedValue"),
        "resting_heart_rate_bpm": stats.get("restingHeartRate"),
        "sleep": sleep_summary(data.get("sleep")),
        "hrv": hrv_summary(data.get("hrv")),
        "training_readiness": latest_readiness(data.get("training_readiness")),
        "latest_activity": latest_activity(data.get("activities")),
        "errors": snapshot.get("errors") or {},
    }


def fmt_duration(seconds: Any) -> str:
    if not isinstance(seconds, (int, float)):
        return "—"
    hours, rem = divmod(int(seconds), 3600)
    minutes = rem // 60
    return f"{hours} h {minutes:02d} min"


def value_or_dash(value: Any) -> str:
    return "—" if value is None else str(value)


def provider_sync_local(value: Any) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(LOCAL_ZONE).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return str(value)


def provider_sync_age_minutes(observed_at: Any, provider_sync_gmt: Any) -> str:
    if not observed_at or not provider_sync_gmt:
        return "—"
    try:
        observed = datetime.fromisoformat(str(observed_at))
        synced = datetime.fromisoformat(str(provider_sync_gmt))
        if synced.tzinfo is None:
            synced = synced.replace(tzinfo=timezone.utc)
        age = max(0, int((observed.astimezone(timezone.utc) - synced.astimezone(timezone.utc)).total_seconds() // 60))
        return str(age)
    except (TypeError, ValueError):
        return "—"


def render_metric(summary: dict[str, Any], today: str) -> str:
    sleep = summary.get("sleep") or {}
    hrv = summary.get("hrv") or {}
    readiness = summary.get("training_readiness") or {}
    activity = summary.get("latest_activity") or {}
    errors = summary.get("errors") or {}
    error_note = "none" if not errors else ", ".join(sorted(errors))
    last_sync_local = provider_sync_local(summary.get("provider_last_sync_gmt"))
    sync_age_minutes = provider_sync_age_minutes(summary.get("observed_at"), summary.get("provider_last_sync_gmt"))
    return f"""---
title: Garmin Current Health and Activity
 type: metric
status: active
created: {today}
updated: {today}
valid_from: {today}
valid_until:
tags: [health, workflow]
sources: [garmin-connect]
confidence: high
contested: false
relations:
  related_to: [\"[[areas/sport-and-physical-practice]]\", \"[[metrics/recovery-2026-07]]\", \"[[metrics/strava-training-history]]\"]
  evidenced_by: []
---
# Garmin Current Health and Activity

> Read-only Garmin Connect retrieval: {summary.get('observed_at')}.
> Device/app data last synced to Garmin: {last_sync_local}; source age at retrieval: {sync_age_minutes} min.
> Steps can be stale when the watch or app has not synced since current movement began.

| Metric | Current value |
|---|---:|
| Steps | {value_or_dash(summary.get('steps'))} |
| Garmin step goal | {value_or_dash(summary.get('step_goal'))} |
| Body Battery | {value_or_dash(summary.get('body_battery_current'))} |
| Resting heart rate | {value_or_dash(summary.get('resting_heart_rate_bpm'))} bpm |
| Sleep | {fmt_duration(sleep.get('sleep_seconds'))} |
| Sleep score | {value_or_dash(sleep.get('sleep_score'))} |
| Last-night HRV | {value_or_dash(hrv.get('last_night_avg_hrv_ms'))} ms |
| HRV status | {value_or_dash(hrv.get('status'))} |
| Training Readiness | {value_or_dash(readiness.get('score'))} |

## Latest activity

- Name: {value_or_dash(activity.get('name'))}
- Type: {value_or_dash(activity.get('type'))}
- Start: {value_or_dash(activity.get('start_local'))}
- Distance: {value_or_dash(activity.get('distance_meters'))} m
- Duration: {fmt_duration(activity.get('duration_seconds'))}

## Collection status

- Endpoint errors: {error_note}
- Authentication tokens are stored locally outside the Wiki.
- Garmin metrics and Strava activity facts keep separate provenance.
""".replace("\n type: metric", "\ntype: metric")


def connect(token_path: Path) -> Garmin:
    client = Garmin()
    client.login(str(token_path))
    return client


def sync_once(client: Any, wiki: Path, now: datetime) -> dict[str, Any]:
    now = now.astimezone(LOCAL_ZONE)
    date = now.date().isoformat()
    data: dict[str, Any] = {}
    errors: dict[str, str] = {}
    call_endpoint("stats", lambda: client.get_stats(date), data, errors)
    call_endpoint("body_battery", lambda: client.get_body_battery(date, date), data, errors)
    call_endpoint("activities", lambda: client.get_activities_by_date(date, date), data, errors)
    raw_day = wiki / "raw/garmin/daily" / date
    morning_path = raw_day / "morning.json"
    if now.hour < 13 or not morning_path.exists():
        call_endpoint("sleep", lambda: client.get_sleep_data(date), data, errors)
        call_endpoint("hrv", lambda: client.get_hrv_data(date), data, errors)
        call_endpoint("training_readiness", lambda: client.get_training_readiness(date), data, errors)
    else:
        try:
            morning = json.loads(morning_path.read_text(encoding="utf-8"))
            morning_data = morning.get("data") or {}
            for name in ("sleep", "hrv", "training_readiness"):
                if name in morning_data:
                    data[name] = morning_data[name]
        except (OSError, ValueError, TypeError):
            call_endpoint("sleep", lambda: client.get_sleep_data(date), data, errors)
            call_endpoint("hrv", lambda: client.get_hrv_data(date), data, errors)
            call_endpoint("training_readiness", lambda: client.get_training_readiness(date), data, errors)
    snapshot = {
        "provider": "garmin-connect",
        "mode": "read-only",
        "observed_at": now.isoformat(timespec="seconds"),
        "date": date,
        "data": data,
        "errors": errors,
    }
    summary = curated(snapshot)
    state = wiki / "_meta/state/garmin-live.json"
    atomic_json(state, snapshot)
    atomic_text(wiki / "metrics/garmin-current.md", render_metric(summary, date))

    sleep = summary.get("sleep") or {}
    if sleep.get("sleep_seconds") and not (raw_day / "morning.json").exists():
        atomic_json(raw_day / "morning.json", snapshot)
    if now.hour >= 23 and not (raw_day / "final.json").exists():
        atomic_json(raw_day / "final.json", snapshot)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--tokens", type=Path, default=DEFAULT_TOKENS)
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()
    client = connect(args.tokens)
    summary = sync_once(client, args.wiki, datetime.now(LOCAL_ZONE))
    if args.print_summary:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
