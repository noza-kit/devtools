from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from feedwatch.paths import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('rss', 'twitch')),
    source TEXT NOT NULL,
    name TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (kind, source)
);

CREATE TABLE IF NOT EXISTS seen_items (
    watch_id INTEGER NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    notified_at TEXT NOT NULL,
    PRIMARY KEY (watch_id, item_id)
);
"""


class WatchNotFoundError(Exception):
    pass


class DuplicateWatchError(Exception):
    pass


@dataclass
class Watch:
    id: int
    kind: str
    source: str
    name: str
    tags: str
    created_at: str

    @property
    def tag_list(self) -> list[str]:
        return [t for t in self.tags.split(",") if t]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect(path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def add_watch(conn: sqlite3.Connection, *, kind: str, source: str, name: str, tags: list[str]) -> Watch:
    try:
        cur = conn.execute(
            "INSERT INTO watches (kind, source, name, tags, created_at) VALUES (?, ?, ?, ?, ?)",
            (kind, source, name, ",".join(tags), _now()),
        )
    except sqlite3.IntegrityError as exc:
        raise DuplicateWatchError(f"already watching {kind} source {source!r}") from exc
    watch = get_watch(conn, cur.lastrowid)
    assert watch is not None
    return watch


def get_watch(conn: sqlite3.Connection, watch_id: int) -> Optional[Watch]:
    row = conn.execute("SELECT * FROM watches WHERE id = ?", (watch_id,)).fetchone()
    return Watch(**dict(row)) if row else None


def list_watches(conn: sqlite3.Connection, *, kind: Optional[str] = None) -> list[Watch]:
    if kind is None:
        rows = conn.execute("SELECT * FROM watches ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM watches WHERE kind = ? ORDER BY id", (kind,)).fetchall()
    return [Watch(**dict(row)) for row in rows]


def remove_watch(conn: sqlite3.Connection, watch_id: int) -> None:
    cur = conn.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
    if cur.rowcount == 0:
        raise WatchNotFoundError(f"no watch with id {watch_id}")


def has_seen(conn: sqlite3.Connection, watch_id: int, item_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM seen_items WHERE watch_id = ? AND item_id = ?", (watch_id, item_id)
    ).fetchone()
    return row is not None


def mark_seen(conn: sqlite3.Connection, watch_id: int, item_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO seen_items (watch_id, item_id, notified_at) VALUES (?, ?, ?)",
        (watch_id, item_id, _now()),
    )
