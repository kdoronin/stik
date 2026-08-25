"""Read-only MCP server exposing Strava coaching data."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import StravaClient
from .core import ConfigStore
from .service import DEFAULT_STREAM_KEYS, StravaService

mcp = FastMCP("Hermes Strava (read-only)")
store = ConfigStore()
service = StravaService(StravaClient(store=store))


@mcp.tool()
def connection_status() -> dict[str, Any]:
    """Check whether Strava OAuth credentials are configured locally."""
    config = store.load()
    athlete = config.get("athlete") or {}
    return {
        "connected": bool(config.get("access_token") and config.get("refresh_token")),
        "athlete_id": athlete.get("id"),
        "athlete_name": " ".join(
            filter(None, [athlete.get("firstname"), athlete.get("lastname")])
        ) or None,
        "scopes": "read,activity:read_all,profile:read_all",
        "mode": "read-only",
    }


@mcp.tool()
def athlete_profile() -> Any:
    """Get the authenticated athlete's Strava profile."""
    return service.athlete_profile()


@mcp.tool()
def athlete_zones() -> Any:
    """Get the athlete's heart-rate and power zones."""
    return service.athlete_zones()


@mcp.tool()
def athlete_stats(athlete_id: int = 0) -> Any:
    """Get recent, year-to-date, and all-time athlete totals."""
    if athlete_id <= 0:
        athlete_id = int((store.load().get("athlete") or {}).get("id") or 0)
    if athlete_id <= 0:
        raise ValueError("athlete_id is required until Strava has been connected")
    return service.athlete_stats(athlete_id)


@mcp.tool()
def recent_activities(
    page: int = 1,
    per_page: int = 30,
    before: int | None = None,
    after: int | None = None,
) -> Any:
    """List activities. before/after are optional Unix timestamps; max 100 per page."""
    return service.recent_activities(
        page=page, per_page=per_page, before=before, after=after
    )


@mcp.tool()
def activity_details(activity_id: int, include_all_efforts: bool = False) -> Any:
    """Get full summary details for one Strava activity."""
    return service.activity_details(
        activity_id, include_all_efforts=include_all_efforts
    )


@mcp.tool()
def activity_laps(activity_id: int) -> Any:
    """Get lap-by-lap metrics for one Strava activity."""
    return service.activity_laps(activity_id)


@mcp.tool()
def activity_streams(
    activity_id: int,
    keys: str = ",".join(DEFAULT_STREAM_KEYS),
) -> Any:
    """Get time-series streams such as HR, pace, cadence, power, altitude, and GPS."""
    return service.activity_streams(activity_id, keys.split(","))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
