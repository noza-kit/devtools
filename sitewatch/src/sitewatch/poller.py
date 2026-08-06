from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any, Mapping, Optional

from notify import notify

from sitewatch.db import Watch, connect, is_due, list_watches, record_check
from sitewatch.scraper import ScrapeError, scrape_selector

logger = logging.getLogger("sitewatch")

DEFAULT_INTERVAL_SECONDS = 1800  # 30 minutes

NotifyConfig = Optional[Mapping[str, Any]]


def check_watch(
    conn: sqlite3.Connection, watch: Watch, *, channels: list[str], notify_config: NotifyConfig = None
) -> bool:
    """Scrape `watch`'s selector; notify + record it if the content changed since last check.

    The very first check for a watch just records a baseline hash (nothing to compare against yet),
    so it never notifies on its own.
    """
    try:
        content = scrape_selector(watch.url, watch.selector)
    except ScrapeError as exc:
        logger.warning("%s (id=%s): %s", watch.name, watch.id, exc)
        return False

    new_hash = content.content_hash
    changed = watch.last_hash is not None and new_hash != watch.last_hash
    if changed:
        notify(f"[{watch.name}] changed: {watch.url}", channels=channels, config=notify_config)

    record_check(conn, watch.id, new_hash)
    return changed


def check_all(conn: sqlite3.Connection, *, channels: list[str], notify_config: NotifyConfig = None) -> int:
    """Check every watch that is due (per its min_interval_sec). Returns how many changes were notified."""
    changed_count = 0
    for watch in list_watches(conn):
        if not is_due(watch):
            continue
        if check_watch(conn, watch, channels=channels, notify_config=notify_config):
            changed_count += 1
        conn.commit()
    return changed_count


def run_forever(
    *,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    channels: list[str],
    notify_config: NotifyConfig = None,
    max_cycles: Optional[int] = None,
) -> None:
    """Wake up every `interval_seconds` and check whichever watches are due, forever (or `max_cycles` times)."""
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        with connect() as conn:
            check_all(conn, channels=channels, notify_config=notify_config)
        cycles += 1
        if max_cycles is None or cycles < max_cycles:
            time.sleep(interval_seconds)
