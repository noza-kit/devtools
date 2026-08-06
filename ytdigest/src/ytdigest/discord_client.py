from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import reqretry
import requests

DISCORD_API_BASE = "https://discord.com/api/v10"
MAX_MESSAGE_LENGTH = 2000

# Discord message-fetch pages max out at 100.
_PAGE_SIZE = 100


class DiscordError(Exception):
    """Raised when a Discord webhook/API call fails or returns an error response."""


def post_webhook(webhook_url: str, content: str) -> str:
    """POST `content` to a Discord webhook and return the created message's id
    (via `?wait=true`, so the id can be recorded for later reply-matching)."""
    if len(content) > MAX_MESSAGE_LENGTH:
        raise DiscordError(
            f"message exceeds Discord's {MAX_MESSAGE_LENGTH}-character limit ({len(content)} chars)"
        )
    try:
        resp = reqretry.post(webhook_url, params={"wait": "true"}, json={"content": content})
    except requests.exceptions.RequestException as exc:
        raise DiscordError(f"failed to post to Discord webhook: {exc}") from exc

    if not (200 <= resp.status_code < 300):
        raise DiscordError(f"Discord webhook returned {resp.status_code}: {resp.text[:200]}")

    return resp.json()["id"]


@dataclass(frozen=True)
class DiscordReply:
    message_id: str
    referenced_message_id: str
    content: str


def fetch_reply_messages(
    bot_token: str, channel_id: str, *, after: Optional[str] = None
) -> tuple[list[DiscordReply], Optional[str]]:
    """Fetch every human (non-bot) reply posted in `channel_id` after the
    message id `after` (exclusive), oldest first. Non-reply messages (no
    `message_reference`) are skipped, since only replies to a notification
    message can be parsed as a dismiss command.

    Returns `(replies, last_seen_message_id)`: the second value is the id of
    the newest message fetched (reply or not), so callers can persist an
    accurate pagination cursor even when the tail of the channel is chatter
    that isn't a reply. It's `after` unchanged if nothing new was fetched."""
    headers = {"Authorization": f"Bot {bot_token}"}
    replies: list[DiscordReply] = []
    cursor = after

    while True:
        params: dict = {"limit": _PAGE_SIZE}
        if cursor:
            params["after"] = cursor
        try:
            resp = reqretry.get(
                f"{DISCORD_API_BASE}/channels/{channel_id}/messages", headers=headers, params=params
            )
        except requests.exceptions.RequestException as exc:
            raise DiscordError(f"failed to fetch messages for channel {channel_id}: {exc}") from exc

        if resp.status_code != 200:
            raise DiscordError(
                f"Discord message history request returned {resp.status_code}: {resp.text[:200]}"
            )

        batch = resp.json()
        if not batch:
            break

        batch.sort(key=lambda m: int(m["id"]))
        for msg in batch:
            cursor = msg["id"]
            if msg.get("author", {}).get("bot"):
                continue
            reference = msg.get("message_reference")
            if not reference or "message_id" not in reference:
                continue
            replies.append(
                DiscordReply(
                    message_id=msg["id"],
                    referenced_message_id=reference["message_id"],
                    content=msg.get("content", ""),
                )
            )

        if len(batch) < _PAGE_SIZE:
            break

    return replies, cursor


def parse_dismiss_numbers(content: str) -> list[int]:
    """Parse a "delete 1,3" (or "delete 1, 3" / "delete 1 3") reply into [1, 3].
    Returns [] if the message doesn't contain a "delete" command."""
    match = re.search("delete", content, re.IGNORECASE)
    if not match:
        return []
    return [int(n) for n in re.findall(r"\d+", content[match.end() :])]
