from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import feedparser
import reqretry

YOUTUBE_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# YouTube channel IDs are always 24 characters starting with "UC".
_YOUTUBE_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")


class FeedFetchError(Exception):
    pass


@dataclass
class FeedEntry:
    """One item (video/post) from an RSS/Atom feed."""

    item_id: str
    title: str
    link: str


def normalize_feed_source(source: str) -> str:
    """Expand a bare YouTube channel ID to its RSS feed URL; pass URLs through unchanged."""
    source = source.strip()
    if _YOUTUBE_CHANNEL_ID_RE.match(source):
        return YOUTUBE_FEED_URL.format(channel_id=source)
    return source


def fetch_entries(feed_url: str) -> list[FeedEntry]:
    """Fetch and parse an RSS/Atom feed (retried via reqretry), newest entries as they appear in the feed."""
    try:
        resp = reqretry.get(feed_url)
        resp.raise_for_status()
    except Exception as exc:
        raise FeedFetchError(f"failed to fetch feed {feed_url}: {exc}") from exc

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        raise FeedFetchError(f"failed to parse feed {feed_url}: {parsed.bozo_exception}")

    entries = []
    for entry in parsed.entries:
        item_id = _entry_id(entry)
        if item_id is None:
            continue
        entries.append(
            FeedEntry(
                item_id=item_id,
                title=entry.get("title", "(no title)"),
                link=entry.get("link", ""),
            )
        )
    return entries


def _entry_id(entry) -> Optional[str]:
    return entry.get("id") or entry.get("guid") or entry.get("link")
