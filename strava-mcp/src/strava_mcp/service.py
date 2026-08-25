"""Read-only coaching-oriented Strava operations."""

from __future__ import annotations

from typing import Any, Sequence

from .client import StravaClient

DEFAULT_STREAM_KEYS = (
    "time",
    "distance",
    "latlng",
    "altitude",
    "velocity_smooth",
    "heartrate",
    "cadence",
    "watts",
    "temp",
    "moving",
    "grade_smooth",
)


class StravaService:
    def __init__(self, client: StravaClient):
        self.client = client

    def athlete_profile(self) -> Any:
        return self.client.get("/athlete")

    def athlete_zones(self) -> Any:
        return self.client.get("/athlete/zones")

    def athlete_stats(self, athlete_id: int) -> Any:
        return self.client.get(f"/athletes/{athlete_id}/stats")

    def recent_activities(
        self,
        *,
        page: int = 1,
        per_page: int = 30,
        before: int | None = None,
        after: int | None = None,
    ) -> Any:
        params: dict[str, Any] = {
            "page": max(1, page),
            "per_page": min(100, max(1, per_page)),
        }
        if before is not None:
            params["before"] = before
        if after is not None:
            params["after"] = after
        return self.client.get("/athlete/activities", params)

    def activity_details(self, activity_id: int, *, include_all_efforts: bool = False) -> Any:
        return self.client.get(
            f"/activities/{activity_id}",
            {"include_all_efforts": str(include_all_efforts).lower()},
        )

    def activity_laps(self, activity_id: int) -> Any:
        return self.client.get(f"/activities/{activity_id}/laps")

    def activity_streams(self, activity_id: int, keys: Sequence[str] = DEFAULT_STREAM_KEYS) -> Any:
        clean_keys = [key.strip() for key in keys if key.strip()]
        return self.client.get(
            f"/activities/{activity_id}/streams",
            {"keys": ",".join(clean_keys), "key_by_type": "true"},
        )
