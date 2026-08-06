from __future__ import annotations

import time
from dataclasses import dataclass

import feedparser
import reqretry
import requests

YOUTUBE_FEED_URL = "https://www.youtube.com/feeds/videos.xml"


class YouTubeError(Exception):
    """Raised when a channel's RSS feed can't be fetched or parsed."""


@dataclass(frozen=True)
class YouTubeVideo:
    video_id: str
    title: str
    url: str
    channel_name: str
    thumbnail_url: str
    published_at: str


def fetch_channel_videos(channel_id: str, *, channel_name: str = "") -> list[YouTubeVideo]:
    """Fetch `channel_id`'s current RSS feed (YouTube keeps roughly the 15 latest
    uploads in it), newest first. `channel_name` overrides the feed's own author
    name for display, since channels.yaml names may differ from the YT handle."""
    try:
        resp = reqretry.get(YOUTUBE_FEED_URL, params={"channel_id": channel_id})
    except requests.exceptions.RequestException as exc:
        raise YouTubeError(f"failed to fetch RSS for channel {channel_id!r}: {exc}") from exc

    if resp.status_code != 200:
        raise YouTubeError(f"RSS for channel {channel_id!r} returned {resp.status_code}")

    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise YouTubeError(f"RSS for channel {channel_id!r} could not be parsed: {feed.bozo_exception}")

    return [_parse_entry(entry, channel_name) for entry in feed.entries]


def _parse_entry(entry, channel_name_override: str) -> YouTubeVideo:
    video_id = getattr(entry, "yt_videoid", "") or entry.get("id", "").rsplit(":", 1)[-1]
    thumbnails = entry.get("media_thumbnail") or [{}]

    return YouTubeVideo(
        video_id=video_id,
        title=entry.get("title", ""),
        url=entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
        channel_name=channel_name_override or entry.get("author", ""),
        thumbnail_url=thumbnails[0].get("url", ""),
        published_at=_normalize_published(entry),
    )


def _normalize_published(entry) -> str:
    parsed = entry.get("published_parsed")
    if parsed:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", parsed)
    return entry.get("published", "")
