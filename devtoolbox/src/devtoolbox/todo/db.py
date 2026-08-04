from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Task:
    id: int
    text: str
    tags: list[str]
    done: bool
    created_at: str
    updated_at: str


def _row_to_task(row: sqlite3.Row) -> Task:
    tags = row["tags"].split(",") if row["tags"] else []
    return Task(
        id=row["id"],
        text=row["text"],
        tags=[t for t in tags if t],
        done=bool(row["done"]),
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
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


class TaskNotFoundError(ValueError):
    pass


def add_task(conn: sqlite3.Connection, text: str, tags: list[str]) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO tasks (text, tags, done, created_at, updated_at) VALUES (?, ?, 0, ?, ?)",
        (text, ",".join(tags), now, now),
    )
    conn.commit()
    return cursor.lastrowid


def get_task(conn: sqlite3.Connection, task_id: int) -> Task | None:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_task(row) if row else None


def list_tasks(
    conn: sqlite3.Connection,
    tags: list[str] | None = None,
    include_done: bool = False,
) -> list[Task]:
    rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    tasks = [_row_to_task(row) for row in rows]
    if not include_done:
        tasks = [t for t in tasks if not t.done]
    if tags:
        tasks = [t for t in tasks if all(tag in t.tags for tag in tags)]
    return tasks


def set_done(conn: sqlite3.Connection, task_id: int, done: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "UPDATE tasks SET done = ?, updated_at = ? WHERE id = ?",
        (int(done), now, task_id),
    )
    conn.commit()
    if cursor.rowcount == 0:
        raise TaskNotFoundError(f"Task #{task_id} not found")


def remove_task(conn: sqlite3.Connection, task_id: int) -> None:
    cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise TaskNotFoundError(f"Task #{task_id} not found")
