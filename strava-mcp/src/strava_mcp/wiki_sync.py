"""Incremental, rate-conscious Strava history ingestion into the LLM Wiki."""

from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .client import StravaClient
from .core import ConfigStore

SOURCE_NOTE = os.environ.get("STRAVA_WIKI_SOURCE_NOTE", "source-notes/strava-history-import")
OVERVIEW = "metrics/strava-training-history"
CONTENT_DIRS = (
    "concepts",
    "areas",
    "projects",
    "entities",
    "decisions",
    "events",
    "metrics",
    "reviews",
    "queries",
    "source-notes",
)


@dataclass(frozen=True)
class SyncSettings:
    wiki: Path
    batch_size: int = 20
    request_delay: float = 2.0


@dataclass(frozen=True)
class SyncResult:
    imported: int
    total: int
    completed: bool
    before: int | None


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _epoch(iso_value: str) -> int:
    return int(datetime.fromisoformat(iso_value.replace("Z", "+00:00")).timestamp())


def _created_for(path: Path, today: str) -> str:
    if path.exists():
        match = re.search(r"(?m)^created:\s*(\d{4}-\d{2}-\d{2})", path.read_text(encoding="utf-8"))
        if match:
            return match.group(1)
    return today


def _duration(seconds: int | float | None) -> str:
    total = int(seconds or 0)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _value(value: Any, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def _activity_date(activity: dict[str, Any]) -> str:
    return str(activity.get("start_date_local") or activity.get("start_date") or "")[:10]


def _render_year_page(path: Path, year: str, activities: list[dict[str, Any]], today: str) -> str:
    rows = []
    for item in sorted(activities, key=lambda x: x.get("start_date", "")):
        rows.append(
            "| {date} | {kind} | {name} | {distance} | {moving} | {elevation} | {avg_hr} | {max_hr} | {power} | {activity_id} |".format(
                date=_activity_date(item),
                kind=str(item.get("type") or item.get("sport_type") or "—").replace("|", "/"),
                name=str(item.get("name") or "—").replace("|", "/").replace("\n", " "),
                distance=_value((item.get("distance") or 0) / 1000, 2),
                moving=_duration(item.get("moving_time")),
                elevation=_value(item.get("total_elevation_gain"), 0),
                avg_hr=_value(item.get("average_heartrate"), 0),
                max_hr=_value(item.get("max_heartrate"), 0),
                power=_value(item.get("average_watts"), 0),
                activity_id=item.get("id", "—"),
            )
        )
    created = _created_for(path, today)
    body = "\n".join(rows) if rows else ""
    return f"""---
title: Strava Activities — {year}
type: review
status: active
created: {created}
updated: {today}
valid_from: {year}-01-01
valid_until: {year}-12-31
tags: [health, monitoring]
sources: [strava]
confidence: high
contested: false
relations:
  part_of: [\"[[sport-and-physical-practice]]\"]
  evidenced_by: [\"[[{SOURCE_NOTE}]]\"]
---
# Strava Activities — {year}

> Structured activity history imported from Strava. Detailed immutable API snapshots are stored under `raw/strava/activities/`.

| date | type | name | km | moving | elevation_m | avg_hr | max_hr | avg_power_w | strava_id |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
{body}

## Related
- [[{OVERVIEW}]]
- [[sport-and-physical-practice]]
- [[{SOURCE_NOTE}]]
"""


def _render_overview(path: Path, activities: list[dict[str, Any]], state: dict[str, Any], today: str) -> str:
    created = _created_for(path, today)
    dates = sorted(filter(None, (_activity_date(item) for item in activities)))
    distance_km = sum(float(item.get("distance") or 0) for item in activities) / 1000
    moving_seconds = sum(int(item.get("moving_time") or 0) for item in activities)
    types = Counter(str(item.get("type") or item.get("sport_type") or "Unknown") for item in activities)
    years = sorted({value[:4] for value in dates if len(value) >= 4})
    status = "Backfill complete" if state.get("completed") else "Backfill in progress"
    type_rows = "\n".join(f"| {kind} | {count} |" for kind, count in sorted(types.items())) or "| — | 0 |"
    year_links = "\n".join(f"- [[metrics/strava-activities-{year}|Strava Activities — {year}]]" for year in years) or "- No activity years imported yet."
    valid_from = dates[0] if dates else today
    valid_until = dates[-1] if dates else ""
    return f"""---
title: Strava Training History
 type: review
status: active
created: {created}
updated: {today}
valid_from: {valid_from}
valid_until: {valid_until}
tags: [health, monitoring]
sources: [strava]
confidence: high
contested: false
relations:
  part_of: [\"[[sport-and-physical-practice]]\"]
  evidenced_by: [\"[[{SOURCE_NOTE}]]\"]
---
# Strava Training History

## Current State
- **Import status:** {status}.
- **Activities imported:** {len(activities)}.
- **Coverage:** {valid_from} → {valid_until or 'pending'}.
- **Requests per scheduled run:** at most {state.get('batch_size', 20) + 1}; runs are spaced to remain far below Strava's default limits.
- **Write access:** disabled; source connection is read-only.

## All-Time Totals Imported So Far
- **Distance:** {distance_km:.2f} km.
- **Moving time:** {_duration(moving_seconds)}.

| activity type | count |
|---|---:|
{type_rows}

## Year Pages
{year_links}

## Provenance and Limits
Raw detailed activity responses are stored as immutable JSON snapshots under `raw/strava/activities/`. Strava does not provide Garmin recovery metrics such as Body Battery or Training Readiness; those remain separate in [[metrics/recovery-2026-07]].

## Related
- [[sport-and-physical-practice]]
- [[metrics/recovery-2026-07]]
- [[{SOURCE_NOTE}]]
""".replace("\n type:", "\ntype:")


def _render_source_note(path: Path, state: dict[str, Any], total: int, today: str) -> str:
    created = _created_for(path, today)
    status = "completed" if state.get("completed") else "in progress"
    return f"""---
title: Strava Full-History Import
type: source-note
status: active
created: {created}
updated: {today}
valid_from: {today}
valid_until:
tags: [health, monitoring, source-note]
sources: [strava]
confidence: high
contested: false
relations:
  related_to: [\"[[sport-and-physical-practice]]\"]
  produces: [\"[[{OVERVIEW}]]\"]
---
# Strava Full-History Import

## Current State
- **Status:** {status}.
- **Detailed activities currently stored:** {total}.
- **Checkpoint (`before` Unix timestamp):** {state.get('before') or 'initial/latest'}.
- **Batch size:** {state.get('batch_size', 20)} activities.
- **Schedule:** conservative recurring batches; no aggressive retries after API errors.

## Method
Each batch requests one activity list page and at most one detailed API response per activity. Completed activity snapshots are deduplicated by Strava activity ID, so retries do not duplicate wiki metrics. The cursor moves backward using the oldest `start_date` in a successfully completed batch.

## Safety
OAuth scopes are `read,activity:read_all,profile:read_all`; no Strava write scopes are present. Tokens remain outside the wiki in a local mode-0600 connector config.

## Related
- [[{OVERVIEW}]]
- [[sport-and-physical-practice]]
- [[metrics/recovery-2026-07]]
"""


def _insert_index_entry(text: str, section: str, entry: str, link: str) -> str:
    if f"[[{link}" in text:
        return text
    heading = f"## {section}"
    if heading not in text:
        return text.rstrip() + f"\n\n{heading}\n\n{entry}\n"
    start = text.index(heading) + len(heading)
    next_heading = text.find("\n## ", start)
    insert_at = len(text) if next_heading < 0 else next_heading
    return text[:insert_at].rstrip() + f"\n\n{entry}\n\n" + text[insert_at:].lstrip("\n")


def _content_page_count(wiki: Path) -> int:
    return sum(1 for directory in CONTENT_DIRS if (wiki / directory).exists() for _ in (wiki / directory).rglob("*.md"))


def _update_index(wiki: Path, years: list[str], today: str) -> None:
    path = wiki / "index.md"
    text = path.read_text(encoding="utf-8")
    text = _insert_index_entry(
        text,
        "Metrics",
        f"- [[{OVERVIEW}|Strava Training History]] — incremental read-only import of detailed all-time Strava activities.",
        OVERVIEW,
    )
    for year in years:
        link = f"metrics/strava-activities-{year}"
        text = _insert_index_entry(
            text,
            "Metrics",
            f"- [[{link}|Strava Activities — {year}]] — one structured row per imported Strava activity.",
            link,
        )
    text = _insert_index_entry(
        text,
        "Source Notes",
        f"- [[{SOURCE_NOTE}|Strava Full-History Import]] — method, checkpoint and provenance for the gradual API backfill.",
        SOURCE_NOTE,
    )
    text = re.sub(r"Last updated: \d{4}-\d{2}-\d{2}", f"Last updated: {today}", text)
    text = re.sub(r"Total content pages: \d+", f"Total content pages: {_content_page_count(wiki)}", text)
    path.write_text(text, encoding="utf-8")


def _load_all_activities(raw_dir: Path) -> list[dict[str, Any]]:
    activities = []
    if not raw_dir.exists():
        return activities
    for path in raw_dir.glob("*.json"):
        value = _read_json(path, {})
        if isinstance(value, dict) and value.get("id"):
            activities.append(value)
    return activities


def sync_once(client: StravaClient, settings: SyncSettings, *, today: str | None = None) -> SyncResult:
    wiki = settings.wiki.expanduser()
    today = today or date.today().isoformat()
    state_path = wiki / "_meta/state/strava-history-sync.json"
    raw_dir = wiki / "raw/strava/activities"
    state = _read_json(state_path, {"before": None, "imported": 0, "completed": False})
    state["batch_size"] = settings.batch_size

    params: dict[str, Any] = {"page": 1, "per_page": settings.batch_size}
    if state.get("before"):
        params["before"] = state["before"]
    summaries = client.get("/athlete/activities", params)
    if not isinstance(summaries, list):
        raise RuntimeError("Strava activity list response was not a list")

    imported = 0
    if summaries:
        for summary in summaries:
            activity_id = int(summary["id"])
            raw_path = raw_dir / f"{activity_id}.json"
            if not raw_path.exists():
                detail = client.get(f"/activities/{activity_id}", {"include_all_efforts": "true"})
                _write_json(raw_path, detail)
                imported += 1
                if settings.request_delay:
                    time.sleep(settings.request_delay)
        state["before"] = min(_epoch(str(item["start_date"])) for item in summaries)
        state["imported"] = int(state.get("imported", 0)) + imported
        state["completed"] = False
    else:
        state["completed"] = True
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    _write_json(state_path, state)

    activities = _load_all_activities(raw_dir)
    by_year: dict[str, list[dict[str, Any]]] = {}
    for activity in activities:
        year = _activity_date(activity)[:4]
        if year:
            by_year.setdefault(year, []).append(activity)
    for year, values in by_year.items():
        path = wiki / f"metrics/strava-activities-{year}.md"
        path.write_text(_render_year_page(path, year, values, today), encoding="utf-8")

    overview_path = wiki / f"{OVERVIEW}.md"
    overview_path.write_text(_render_overview(overview_path, activities, state, today), encoding="utf-8")
    source_path = wiki / f"{SOURCE_NOTE}.md"
    source_path.write_text(_render_source_note(source_path, state, len(activities), today), encoding="utf-8")
    _update_index(wiki, sorted(by_year), today)

    with (wiki / "log.md").open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n## [{today}] ingest | Strava history batch\n\n"
            f"- Imported {imported} new detailed activities; {len(activities)} total raw snapshots.\n"
            f"- Backfill completed: {str(bool(state.get('completed'))).lower()}; next before cursor: {state.get('before')}.\n"
            f"- Updated `{OVERVIEW}.md`, yearly metrics pages, `{SOURCE_NOTE}.md` and `index.md`.\n"
            f"- API budget for this run: at most {settings.batch_size + 1} requests; configured delay {settings.request_delay}s between details.\n"
        )

    return SyncResult(
        imported=imported,
        total=len(activities),
        completed=bool(state.get("completed")),
        before=state.get("before"),
    )


def main() -> None:
    wiki = Path(os.environ.get("WIKI_PATH", Path.home() / "wiki"))
    batch_size = int(os.environ.get("STRAVA_WIKI_BATCH_SIZE", "20"))
    request_delay = float(os.environ.get("STRAVA_WIKI_REQUEST_DELAY", "2"))
    result = sync_once(
        StravaClient(store=ConfigStore()),
        SyncSettings(wiki=wiki, batch_size=batch_size, request_delay=request_delay),
    )
    if result.completed:
        print(f"Strava full-history backfill complete: {result.total} activities stored in the LLM Wiki.")


if __name__ == "__main__":
    main()
