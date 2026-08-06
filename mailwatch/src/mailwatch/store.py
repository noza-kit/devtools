from __future__ import annotations

import sqlite3
from pathlib import Path


class SeenStore:
    """Tracks Gmail message IDs already processed, so a restart or an
    overlapping poll window never sends a duplicate notification."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_messages (
                message_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL,
                matched_rules TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def is_seen(self, message_id: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM seen_messages WHERE message_id = ?", (message_id,))
        return cur.fetchone() is not None

    def mark_seen(self, message_id: str, matched_rules: list[str]) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_messages (message_id, processed_at, matched_rules) "
            "VALUES (?, datetime('now'), ?)",
            (message_id, ",".join(matched_rules)),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SeenStore":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
