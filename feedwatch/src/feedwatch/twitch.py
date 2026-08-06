from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping, Optional

import reqretry

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
STREAMS_URL = "https://api.twitch.tv/helix/streams"

Config = Optional[Mapping[str, Any]]


class TwitchConfigError(Exception):
    pass


class TwitchAPIError(Exception):
    pass


@dataclass
class StreamInfo:
    """A currently-live broadcast, as returned by the Helix Get Streams endpoint."""

    stream_id: str  # unique per broadcast session; changes each time the channel goes live
    title: str
    user_name: str
    user_login: str

    @property
    def url(self) -> str:
        return f"https://www.twitch.tv/{self.user_login}"


def _get_setting(name: str, config: Config) -> Optional[str]:
    """Resolve a setting from `config` (dict/confload.Config-like) first, then env vars."""
    if config is not None:
        try:
            value = config[name.lower()]
        except (KeyError, TypeError):
            value = None
        if value is not None:
            return str(value)
    return os.environ.get(name)


def load_credentials(config: Config = None) -> tuple[str, str]:
    """Read TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET from config or env vars.

    Requires a Twitch Developer application (https://dev.twitch.tv/console/apps)
    to obtain a client id/secret - see the feedwatch README.
    """
    client_id = _get_setting("TWITCH_CLIENT_ID", config)
    client_secret = _get_setting("TWITCH_CLIENT_SECRET", config)
    if not client_id or not client_secret:
        raise TwitchConfigError(
            "TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET are not set (env vars or config). "
            "Register an application at https://dev.twitch.tv/console/apps to obtain them."
        )
    return client_id, client_secret


class TwitchClient:
    """Minimal Helix client: app access token (client-credentials flow) + Get Streams."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None

    def _fetch_app_token(self) -> str:
        resp = reqretry.post(
            TOKEN_URL,
            params={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        )
        if resp.status_code != 200:
            raise TwitchAPIError(f"token request failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()["access_token"]

    def _headers(self) -> dict[str, str]:
        if self._access_token is None:
            self._access_token = self._fetch_app_token()
        return {"Client-Id": self.client_id, "Authorization": f"Bearer {self._access_token}"}

    def get_live_stream(self, user_login: str) -> Optional[StreamInfo]:
        """Return the current live stream for `user_login`, or None if the channel is offline."""
        resp = reqretry.get(STREAMS_URL, headers=self._headers(), params={"user_login": user_login})
        if resp.status_code == 401:
            # App token expired/revoked - fetch a fresh one and retry once.
            self._access_token = self._fetch_app_token()
            resp = reqretry.get(STREAMS_URL, headers=self._headers(), params={"user_login": user_login})
        if resp.status_code != 200:
            raise TwitchAPIError(f"get streams failed ({resp.status_code}): {resp.text[:200]}")

        data = resp.json().get("data", [])
        if not data:
            return None
        item = data[0]
        return StreamInfo(
            stream_id=item["id"],
            title=item.get("title", "(no title)"),
            user_name=item.get("user_name", user_login),
            user_login=item.get("user_login", user_login),
        )
