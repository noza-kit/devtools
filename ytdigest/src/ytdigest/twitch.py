from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

import reqretry
import requests

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
API_BASE = "https://api.twitch.tv/helix"

# Twitch batches user_login/user_id filters at up to 100 per request.
_BATCH_SIZE = 100


class TwitchError(Exception):
    """Raised when a Twitch API call fails or returns an error response."""


class TwitchConfigError(TwitchError):
    """Raised for missing/invalid Twitch API credentials."""


@dataclass(frozen=True)
class TwitchStream:
    stream_id: str
    user_login: str
    user_name: str
    title: str
    started_at: str
    thumbnail_url: str


@dataclass(frozen=True)
class TwitchVideo:
    video_id: str
    title: str
    url: str
    thumbnail_url: str
    created_at: str
    published_at: str


@dataclass
class TwitchClient:
    """Twitch Helix API client authenticated via the Client Credentials flow.

    Client Credentials tokens carry no user context, which is fine here: every
    endpoint used (streams/users/videos) only needs an app access token, not a
    user login.
    """

    client_id: str
    client_secret: str
    _session: reqretry.Session = field(default_factory=reqretry.Session, init=False, repr=False)
    _token: Optional[str] = field(default=None, init=False, repr=False)
    _token_expires_at: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.client_id or not self.client_secret:
            raise TwitchConfigError("Twitch client_id and client_secret are required")

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "TwitchClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _fetch_token(self) -> str:
        try:
            resp = self._session.post(
                TOKEN_URL,
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
            )
        except requests.exceptions.RequestException as exc:
            raise TwitchError(f"failed to obtain Twitch access token: {exc}") from exc

        if resp.status_code != 200:
            raise TwitchError(f"Twitch token request returned {resp.status_code}: {resp.text[:200]}")

        payload = resp.json()
        self._token = payload["access_token"]
        # Refresh a minute early so a call doesn't race token expiry mid-request.
        self._token_expires_at = time.time() + payload.get("expires_in", 0) - 60
        return self._token

    def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token
        return self._fetch_token()

    def _get(self, path: str, params) -> dict:
        headers = {"Client-Id": self.client_id, "Authorization": f"Bearer {self._ensure_token()}"}
        try:
            resp = self._session.get(f"{API_BASE}{path}", headers=headers, params=params)
        except requests.exceptions.RequestException as exc:
            raise TwitchError(f"Twitch API request to {path} failed: {exc}") from exc

        if resp.status_code == 401:
            # The cached token may have just expired server-side; refresh once and retry.
            headers["Authorization"] = f"Bearer {self._fetch_token()}"
            try:
                resp = self._session.get(f"{API_BASE}{path}", headers=headers, params=params)
            except requests.exceptions.RequestException as exc:
                raise TwitchError(f"Twitch API request to {path} failed: {exc}") from exc

        if resp.status_code != 200:
            raise TwitchError(f"Twitch API {path} returned {resp.status_code}: {resp.text[:200]}")

        return resp.json()

    def get_live_streams(self, logins: Iterable[str]) -> dict[str, TwitchStream]:
        """Returns {login (lowercase): TwitchStream} for channels currently live."""
        logins = list(logins)
        live: dict[str, TwitchStream] = {}
        for batch in _chunks(logins, _BATCH_SIZE):
            payload = self._get("/streams", params=[("user_login", login) for login in batch])
            for item in payload.get("data", []):
                login = item["user_login"].lower()
                live[login] = TwitchStream(
                    stream_id=item.get("id", ""),
                    user_login=item["user_login"],
                    user_name=item.get("user_name", item["user_login"]),
                    title=item.get("title", ""),
                    started_at=item.get("started_at", ""),
                    thumbnail_url=_render_thumbnail(item.get("thumbnail_url", ""), "{width}", "{height}"),
                )
        return live

    def get_user_id(self, login: str) -> Optional[str]:
        payload = self._get("/users", params={"login": login})
        data = payload.get("data", [])
        return data[0]["id"] if data else None

    def get_latest_vod(self, login: str, *, after: Optional[str] = None) -> Optional[TwitchVideo]:
        """The most recent 'archive' (past broadcast) VOD for `login`, or None if
        it has none yet (e.g. the VOD hasn't finished processing). `after`
        (an RFC3339 timestamp) filters out VODs created before a known stream
        start, so a channel that has gone live/offline again isn't matched to a
        stale VOD from before it."""
        user_id = self.get_user_id(login)
        if user_id is None:
            return None

        payload = self._get("/videos", params={"user_id": user_id, "type": "archive", "first": 5})
        candidates = payload.get("data", [])
        if after:
            after_matches = [v for v in candidates if v.get("created_at", "") >= after]
            if after_matches:
                candidates = after_matches

        if not candidates:
            return None

        video = candidates[0]
        return TwitchVideo(
            video_id=video["id"],
            title=video.get("title", ""),
            url=video.get("url", f"https://www.twitch.tv/videos/{video['id']}"),
            thumbnail_url=_render_thumbnail(video.get("thumbnail_url", ""), "%{width}", "%{height}"),
            created_at=video.get("created_at", ""),
            published_at=video.get("published_at", video.get("created_at", "")),
        )


def _render_thumbnail(template: str, width_token: str, height_token: str, *, width: str = "440", height: str = "248") -> str:
    if not template:
        return ""
    return template.replace(width_token, width).replace(height_token, height)


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]
