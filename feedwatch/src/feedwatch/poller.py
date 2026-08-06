from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any, Mapping, Optional

from notify import notify

from feedwatch.db import Watch, connect, has_seen, list_watches, mark_seen
from feedwatch.feeds import FeedFetchError, fetch_entries
from feedwatch.twitch import TwitchAPIError, TwitchClient, TwitchConfigError, load_credentials

logger = logging.getLogger("feedwatch")

DEFAULT_INTERVAL_SECONDS = 600  # 10 minutes

NotifyConfig = Optional[Mapping[str, Any]]


def check_rss_watch(
    conn: sqlite3.Connection, watch: Watch, *, channels: list[str], notify_config: NotifyConfig = None
) -> int:
    """Fetch `watch`'s feed, notify + record any not-yet-seen entries. Returns how many were new."""
    try:
        entries = fetch_entries(watch.source)
    except FeedFetchError as exc:
        logger.warning("%s (id=%s): %s", watch.name, watch.id, exc)
        return 0

    new_count = 0
    for entry in entries:
        if has_seen(conn, watch.id, entry.item_id):
            continue
        notify(f"[{watch.name}] {entry.title}\n{entry.link}", channels=channels, config=notify_config)
        mark_seen(conn, watch.id, entry.item_id)
        new_count += 1
    return new_count


def check_twitch_watch(
    conn: sqlite3.Connection,
    watch: Watch,
    client: TwitchClient,
    *,
    channels: list[str],
    notify_config: NotifyConfig = None,
) -> int:
    """Check if `watch`'s channel is live; notify + record it if this broadcast hasn't been seen yet."""
    try:
        stream = client.get_live_stream(watch.source)
    except TwitchAPIError as exc:
        logger.warning("%s (id=%s): %s", watch.name, watch.id, exc)
        return 0

    if stream is None or has_seen(conn, watch.id, stream.stream_id):
        return 0

    notify(f"[{watch.name}] LIVE: {stream.title}\n{stream.url}", channels=channels, config=notify_config)
    mark_seen(conn, watch.id, stream.stream_id)
    return 1


def build_twitch_client(config: NotifyConfig = None) -> Optional[TwitchClient]:
    """Build a TwitchClient from configured credentials, or None if they aren't set."""
    try:
        client_id, client_secret = load_credentials(config)
    except TwitchConfigError:
        return None
    return TwitchClient(client_id, client_secret)


def check_all(
    conn: sqlite3.Connection,
    *,
    channels: list[str],
    notify_config: NotifyConfig = None,
    twitch_client: Optional[TwitchClient] = None,
) -> int:
    """Run one check pass over every registered watch. Returns the number of new notifications sent."""
    notified = 0
    for watch in list_watches(conn):
        if watch.kind == "rss":
            notified += check_rss_watch(conn, watch, channels=channels, notify_config=notify_config)
        elif watch.kind == "twitch":
            if twitch_client is None:
                logger.warning(
                    "skipping twitch watch %s (id=%s): no Twitch credentials configured", watch.name, watch.id
                )
                continue
            notified += check_twitch_watch(
                conn, watch, twitch_client, channels=channels, notify_config=notify_config
            )
        conn.commit()
    return notified


def run_forever(
    *,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    channels: list[str],
    notify_config: NotifyConfig = None,
    max_cycles: Optional[int] = None,
) -> None:
    """Poll every registered watch every `interval_seconds`, forever (or `max_cycles` times, for tests)."""
    twitch_client = build_twitch_client(notify_config)
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        with connect() as conn:
            check_all(conn, channels=channels, notify_config=notify_config, twitch_client=twitch_client)
        cycles += 1
        if max_cycles is None or cycles < max_cycles:
            time.sleep(interval_seconds)
