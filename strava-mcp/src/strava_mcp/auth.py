"""OAuth token exchange helpers."""

from __future__ import annotations

from typing import Any

from .client import TOKEN_URL, Transport, default_transport
from .core import ConfigStore


def complete_authorization(
    *,
    store: ConfigStore,
    client_id: str,
    client_secret: str,
    code: str,
    transport: Transport = default_transport,
) -> dict[str, Any]:
    response = transport(
        "POST",
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    if not isinstance(response, dict) or not response.get("access_token"):
        raise RuntimeError("Strava returned an invalid authorization response")
    athlete = response.get("athlete") or {}
    store.save(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "access_token": response["access_token"],
            "refresh_token": response["refresh_token"],
            "expires_at": response.get("expires_at", 0),
            "athlete": athlete,
        }
    )
    return athlete
