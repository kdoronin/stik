"""Authenticated read-only Strava API client."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .core import ConfigStore, merge_token_response

API_BASE = "https://www.strava.com/api/v3"
TOKEN_URL = "https://www.strava.com/oauth/token"

Transport = Callable[..., dict[str, Any] | list[Any]]


def default_transport(
    method: str,
    url: str,
    *,
    data: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any] | list[Any]:
    body = urlencode(data).encode() if data is not None else None
    request_headers = dict(headers or {})
    if body is not None:
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request_headers.setdefault("Accept", "application/json")
    req = Request(url, data=body, headers=request_headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Strava API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Strava API: {exc.reason}") from exc


class StravaClient:
    def __init__(
        self,
        *,
        store: ConfigStore | None = None,
        transport: Transport = default_transport,
        now: Callable[[], float] = time.time,
    ):
        self.store = store or ConfigStore()
        self.transport = transport
        self.now = now

    def access_token(self) -> str:
        config = self.store.load()
        token = config.get("access_token")
        if not token:
            raise RuntimeError("Strava is not connected. Run strava-auth first.")
        if int(config.get("expires_at", 0)) > int(self.now()) + 60:
            return str(token)

        required = ("client_id", "client_secret", "refresh_token")
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise RuntimeError(f"Cannot refresh Strava token; missing: {', '.join(missing)}")
        response = self.transport(
            "POST",
            TOKEN_URL,
            data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "grant_type": "refresh_token",
                "refresh_token": config["refresh_token"],
            },
        )
        if not isinstance(response, dict) or not response.get("access_token"):
            raise RuntimeError("Strava returned an invalid token refresh response")
        merged = merge_token_response(config, response)
        self.store.save(merged)
        return str(merged["access_token"])

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        url = f"{API_BASE}{path}"
        if params:
            filtered = {key: value for key, value in params.items() if value is not None}
            if filtered:
                url = f"{url}?{urlencode(filtered)}"
        return self.transport(
            "GET",
            url,
            headers={"Authorization": f"Bearer {self.access_token()}"},
        )
