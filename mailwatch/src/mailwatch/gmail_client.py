from __future__ import annotations

import base64
from typing import Optional

import reqretry

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Cap per poll cycle: this is a personal-inbox watcher, not a bulk sync tool,
# and the configured `gmail.query` (e.g. "newer_than:1d") already narrows
# the window, so pagination beyond this would just be quota waste.
DEFAULT_MAX_RESULTS = 50


class GmailApiError(Exception):
    pass


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _get(access_token: str, path: str, *, params: Optional[dict] = None) -> dict:
    resp = reqretry.get(f"{GMAIL_API_BASE}{path}", headers=_headers(access_token), params=params)
    if resp.status_code != 200:
        raise GmailApiError(f"Gmail API {path} returned {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def list_message_ids(access_token: str, query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> list[str]:
    """List message IDs matching `query` (Gmail search syntax), capped at `max_results`."""
    ids: list[str] = []
    page_token: Optional[str] = None
    while len(ids) < max_results:
        params = {"q": query, "maxResults": min(50, max_results - len(ids))}
        if page_token:
            params["pageToken"] = page_token
        data = _get(access_token, "/messages", params=params)
        ids.extend(m["id"] for m in data.get("messages", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return ids


def get_message(access_token: str, message_id: str) -> dict:
    """Fetch a single message with headers and full body/attachment metadata."""
    return _get(access_token, f"/messages/{message_id}", params={"format": "full"})


def get_attachment_data(access_token: str, message_id: str, attachment_id: str) -> bytes:
    data = _get(access_token, f"/messages/{message_id}/attachments/{attachment_id}")
    raw = data["data"]
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
