from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Snippet:
    name: str
    content: str
    tags: list[str]
    created_at: str
    updated_at: str


def _row_to_snippet(row: sqlite3.Row) -> Snippet:
    tags = row["tags"].split(",") if row["tags"] else []
    return Snippet(
        name=row["name"],
        content=row["content"],
        tags=[t for t in tags if t],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS snippets (
            name TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


class SnippetExistsError(ValueError):
    pass


class SnippetNotFoundError(ValueError):
    pass


def add_snippet(
    conn: sqlite3.Connection,
    name: str,
    content: str,
    tags: list[str],
    overwrite: bool = False,
) -> None:
    existing = get_snippet(conn, name)
    now = datetime.now(timezone.utc).isoformat()
    tags_str = ",".join(tags)

    if existing is not None and not overwrite:
        raise SnippetExistsError(f"Snippet '{name}' already exists")

    if existing is not None:
        conn.execute(
            "UPDATE snippets SET content = ?, tags = ?, updated_at = ? WHERE name = ?",
            (content, tags_str, now, name),
        )
    else:
        conn.execute(
            "INSERT INTO snippets (name, content, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, content, tags_str, now, now),
        )
    conn.commit()


def get_snippet(conn: sqlite3.Connection, name: str) -> Snippet | None:
    row = conn.execute("SELECT * FROM snippets WHERE name = ?", (name,)).fetchone()
    return _row_to_snippet(row) if row else None


def list_snippets(conn: sqlite3.Connection, tag: str | None = None) -> list[Snippet]:
    rows = conn.execute("SELECT * FROM snippets ORDER BY name").fetchall()
    snippets = [_row_to_snippet(row) for row in rows]
    if tag:
        snippets = [s for s in snippets if tag in s.tags]
    return snippets


def search_snippets(conn: sqlite3.Connection, keyword: str) -> list[Snippet]:
    like = f"%{keyword}%"
    rows = conn.execute(
        "SELECT * FROM snippets WHERE name LIKE ? OR tags LIKE ? OR content LIKE ? "
        "ORDER BY name",
        (like, like, like),
    ).fetchall()
    return [_row_to_snippet(row) for row in rows]


def remove_snippet(conn: sqlite3.Connection, name: str) -> None:
    cursor = conn.execute("DELETE FROM snippets WHERE name = ?", (name,))
    conn.commit()
    if cursor.rowcount == 0:
        raise SnippetNotFoundError(f"Snippet '{name}' not found")
