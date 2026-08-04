from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Run:
    id: int
    timestamp: str
    params: dict
    results: dict
    tags: list[str]


def _row_to_run(row: sqlite3.Row) -> Run:
    tags = row["tags"].split(",") if row["tags"] else []
    return Run(
        id=row["id"],
        timestamp=row["timestamp"],
        params=json.loads(row["params"]),
        results=json.loads(row["results"]),
        tags=[t for t in tags if t],
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
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            params TEXT NOT NULL,
            results TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.commit()


class RunNotFoundError(ValueError):
    pass


def insert_run(
    conn: sqlite3.Connection,
    params: dict,
    results: dict,
    tags: list[str] | None = None,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO runs (timestamp, params, results, tags) VALUES (?, ?, ?, ?)",
        (
            now,
            json.dumps(params, ensure_ascii=False, default=str),
            json.dumps(results, ensure_ascii=False, default=str),
            ",".join(tags or []),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_run(conn: sqlite3.Connection, run_id: int) -> Run | None:
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return _row_to_run(row) if row else None


def list_runs(
    conn: sqlite3.Connection,
    tags: list[str] | None = None,
    limit: int | None = None,
) -> list[Run]:
    """Runs ordered most-recent-first, optionally filtered by tag and capped at `limit`."""
    rows = conn.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
    runs = [_row_to_run(row) for row in rows]
    if tags:
        runs = [r for r in runs if all(tag in r.tags for tag in tags)]
    if limit is not None:
        runs = runs[:limit]
    return runs
