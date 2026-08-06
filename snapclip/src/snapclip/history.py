from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PIL import Image

DEFAULT_HOME = Path.home() / ".snapclip"
DEFAULT_DB_PATH = DEFAULT_HOME / "history.db"
DEFAULT_IMAGE_DIR = DEFAULT_HOME / "history_images"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('text', 'image')),
    content TEXT NOT NULL,   -- the text itself, or an image file path
    created_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class HistoryEntry:
    id: int
    kind: str
    content: str
    created_at: str

    def preview(self, max_len: int = 60) -> str:
        if self.kind == "image":
            return f"[image] {Path(self.content).name}"
        text = self.content.replace("\n", " ").strip()
        return text if len(text) <= max_len else text[: max_len - 1] + "…"


class HistoryStore:
    def __init__(self, db_path: Optional[Path] = None, image_dir: Optional[Path] = None):
        # Resolved here (not as default-argument values) so monkeypatching
        # module-level DEFAULT_DB_PATH/DEFAULT_IMAGE_DIR in tests works.
        self.db_path = db_path or DEFAULT_DB_PATH
        self.image_dir = image_dir or DEFAULT_IMAGE_DIR
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "HistoryStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def add_text(self, text: str, now: Optional[datetime] = None) -> int:
        return self._insert("text", text, now)

    def add_image(self, image: Image.Image, now: Optional[datetime] = None) -> int:
        now = now or datetime.now(timezone.utc)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{now.strftime('%Y%m%d_%H%M%S_%f')}.png"
        path = self.image_dir / filename
        image.save(path)
        return self._insert("image", str(path), now)

    def _insert(self, kind: str, content: str, now: Optional[datetime]) -> int:
        now = now or datetime.now(timezone.utc)
        cur = self._conn.execute(
            "INSERT INTO history (kind, content, created_at) VALUES (?, ?, ?)",
            (kind, content, now.isoformat()),
        )
        self._conn.commit()
        return cur.lastrowid

    def all(self, limit: int = 200) -> list[HistoryEntry]:
        rows = self._conn.execute(
            "SELECT id, kind, content, created_at FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [HistoryEntry(*row) for row in rows]

    def get(self, entry_id: int) -> Optional[HistoryEntry]:
        row = self._conn.execute(
            "SELECT id, kind, content, created_at FROM history WHERE id = ?", (entry_id,)
        ).fetchone()
        return HistoryEntry(*row) if row else None


def filter_entries(entries: list[HistoryEntry], query: str) -> list[HistoryEntry]:
    """Case-insensitive substring filter over each entry's preview text,
    used by both the interactive TUI and directly in tests. Empty query
    returns everything unfiltered."""
    if not query:
        return list(entries)
    needle = query.lower()
    return [e for e in entries if needle in e.preview(max_len=10_000).lower()]
