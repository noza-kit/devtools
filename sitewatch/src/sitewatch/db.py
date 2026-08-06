from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from sitewatch.paths import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    selector TEXT NOT NULL,
    name TEXT NOT NULL,
    min_interval_sec INTEGER NOT NULL DEFAULT 1800,
    last_hash TEXT,
    last_checked_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (url, selector)
);
"""

DEFAULT_MIN_INTERVAL_SECONDS = 1800  # 30 minutes


class WatchNotFoundError(Exception):
    pass


class DuplicateWatchError(Exception):
    pass


@dataclass
class Watch:
    id: int
    url: str
    selector: str
    name: str
    min_interval_sec: int
    last_hash: Optional[str]
    last_checked_at: Optional[str]
    created_at: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def connect(path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def add_watch(
    conn: sqlite3.Connection,
    *,
    url: str,
    selector: str,
    name: str,
    min_interval_sec: int = DEFAULT_MIN_INTERVAL_SECONDS,
) -> Watch:
    try:
        cur = conn.execute(
            "INSERT INTO watches (url, selector, name, min_interval_sec, created_at) VALUES (?, ?, ?, ?, ?)",
            (url, selector, name, min_interval_sec, _now().isoformat()),
        )
    except sqlite3.IntegrityError as exc:
        raise DuplicateWatchError(f"already watching selector {selector!r} on {url!r}") from exc
    watch = get_watch(conn, cur.lastrowid)
    assert watch is not None
    return watch


def get_watch(conn: sqlite3.Connection, watch_id: int) -> Optional[Watch]:
    row = conn.execute("SELECT * FROM watches WHERE id = ?", (watch_id,)).fetchone()
    return Watch(**dict(row)) if row else None


def list_watches(conn: sqlite3.Connection) -> list[Watch]:
    rows = conn.execute("SELECT * FROM watches ORDER BY id").fetchall()
    return [Watch(**dict(row)) for row in rows]


def remove_watch(conn: sqlite3.Connection, watch_id: int) -> None:
    cur = conn.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
    if cur.rowcount == 0:
        raise WatchNotFoundError(f"no watch with id {watch_id}")


def record_check(conn: sqlite3.Connection, watch_id: int, content_hash: str) -> None:
    conn.execute(
        "UPDATE watches SET last_hash = ?, last_checked_at = ? WHERE id = ?",
        (content_hash, _now().isoformat(), watch_id),
    )


def is_due(watch: Watch, *, now: Optional[datetime] = None) -> bool:
    """Whether `watch` has gone unchecked for at least its min_interval_sec."""
    if watch.last_checked_at is None:
        return True
    now = now or _now()
    elapsed = (now - datetime.fromisoformat(watch.last_checked_at)).total_seconds()
    return elapsed >= watch.min_interval_sec
