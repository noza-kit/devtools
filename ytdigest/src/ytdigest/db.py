from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    platform           TEXT NOT NULL CHECK (platform IN ('youtube', 'twitch')),
    type               TEXT NOT NULL CHECK (type IN ('video', 'live', 'vod')),
    title              TEXT NOT NULL,
    channel_name       TEXT NOT NULL,
    url                TEXT NOT NULL UNIQUE,
    thumbnail_url      TEXT,
    published_at       TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'pending'
                           CHECK (status IN ('pending', 'archived', 'dismissed')),
    notified_at        TEXT,
    notify_message_id  TEXT,
    notify_number      INTEGER,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_notify_message ON items(notify_message_id);

CREATE TABLE IF NOT EXISTS live_tracking (
    channel_name TEXT PRIMARY KEY,
    item_id      INTEGER NOT NULL REFERENCES items(id),
    started_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


@dataclass
class Item:
    platform: str
    type: str
    title: str
    channel_name: str
    url: str
    published_at: str
    thumbnail_url: Optional[str] = None
    status: str = "pending"
    notified_at: Optional[str] = None
    notify_message_id: Optional[str] = None
    notify_number: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Item":
        return cls(**{k: row[k] for k in row.keys()})


@dataclass
class LiveTracking:
    channel_name: str
    item_id: int
    started_at: str


class Database:
    """Thin sqlite3 wrapper over the ytdigest schema."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- items -----------------------------------------------------------------

    def add_item(self, item: Item) -> Optional[int]:
        """Insert `item`. Returns its new id, or None if `url` already exists (no-op)."""
        cur = self._conn.execute(
            """
            INSERT OR IGNORE INTO items
                (platform, type, title, channel_name, url, thumbnail_url, published_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.platform,
                item.type,
                item.title,
                item.channel_name,
                item.url,
                item.thumbnail_url,
                item.published_at,
                item.status,
            ),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            return None
        return cur.lastrowid

    def get_item(self, item_id: int) -> Optional[Item]:
        row = self._conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return Item.from_row(row) if row else None

    def get_item_by_url(self, url: str) -> Optional[Item]:
        row = self._conn.execute("SELECT * FROM items WHERE url = ?", (url,)).fetchone()
        return Item.from_row(row) if row else None

    def get_items_by_status(self, status: str) -> list[Item]:
        rows = self._conn.execute(
            "SELECT * FROM items WHERE status = ? ORDER BY id", (status,)
        ).fetchall()
        return [Item.from_row(r) for r in rows]

    def get_item_by_notify(self, message_id: str, number: int) -> Optional[Item]:
        row = self._conn.execute(
            "SELECT * FROM items WHERE notify_message_id = ? AND notify_number = ?",
            (message_id, number),
        ).fetchone()
        return Item.from_row(row) if row else None

    def set_status(self, item_id: int, status: str) -> None:
        self._conn.execute("UPDATE items SET status = ? WHERE id = ?", (status, item_id))
        self._conn.commit()

    def mark_notified(self, item_id: int, *, message_id: str, number: int, notified_at: str) -> None:
        self._conn.execute(
            """
            UPDATE items
               SET notified_at = ?, notify_message_id = ?, notify_number = ?
             WHERE id = ?
            """,
            (notified_at, message_id, number, item_id),
        )
        self._conn.commit()

    def get_stale_pending_items(self, cutoff: str) -> list[Item]:
        """Pending items notified at/before `cutoff` (ISO8601) that aren't
        being tracked as a still-live stream (see `live_tracking`)."""
        rows = self._conn.execute(
            """
            SELECT * FROM items
             WHERE status = 'pending'
               AND notified_at IS NOT NULL
               AND notified_at <= ?
               AND id NOT IN (SELECT item_id FROM live_tracking)
             ORDER BY id
            """,
            (cutoff,),
        ).fetchall()
        return [Item.from_row(r) for r in rows]

    # -- live_tracking -----------------------------------------------------------

    def add_live_tracking(self, channel_name: str, item_id: int, started_at: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO live_tracking (channel_name, item_id, started_at) VALUES (?, ?, ?)",
            (channel_name, item_id, started_at),
        )
        self._conn.commit()

    def get_live_tracking(self, channel_name: str) -> Optional[LiveTracking]:
        row = self._conn.execute(
            "SELECT * FROM live_tracking WHERE channel_name = ?", (channel_name,)
        ).fetchone()
        return LiveTracking(**dict(row)) if row else None

    def list_live_tracking(self) -> list[LiveTracking]:
        rows = self._conn.execute("SELECT * FROM live_tracking ORDER BY channel_name").fetchall()
        return [LiveTracking(**dict(r)) for r in rows]

    def remove_live_tracking(self, channel_name: str) -> None:
        self._conn.execute("DELETE FROM live_tracking WHERE channel_name = ?", (channel_name,))
        self._conn.commit()

    # -- meta ----------------------------------------------------------------

    def get_meta(self, key: str) -> Optional[str]:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
        self._conn.commit()
