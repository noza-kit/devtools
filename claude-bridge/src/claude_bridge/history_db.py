from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_alias  TEXT NOT NULL,
    user_id        TEXT NOT NULL,
    instruction    TEXT NOT NULL,
    mode           TEXT NOT NULL CHECK (mode IN ('diff', 'summary')),
    status         TEXT NOT NULL
                       CHECK (status IN ('running', 'completed', 'failed', 'timeout', 'cancelled')),
    result_summary TEXT,
    session_id     TEXT,
    started_at     TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_alias);

CREATE TABLE IF NOT EXISTS sessions (
    project_alias TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@dataclass
class Run:
    project_alias: str
    user_id: str
    instruction: str
    mode: str
    status: str = "running"
    result_summary: Optional[str] = None
    session_id: Optional[str] = None
    id: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Run":
        return cls(**{k: row[k] for k in row.keys()})


class HistoryDB:
    """Thin sqlite3 wrapper logging every instruction/result exchanged with
    Claude Code, plus the last Claude session id per project (used to pass
    `--resume` on the next instruction for that project)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "HistoryDB":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- runs --------------------------------------------------------------

    def start_run(self, *, project_alias: str, user_id: str, instruction: str, mode: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO runs (project_alias, user_id, instruction, mode, status) "
            "VALUES (?, ?, ?, ?, 'running')",
            (project_alias, user_id, instruction, mode),
        )
        self._conn.commit()
        return cur.lastrowid

    def finish_run(
        self, run_id: int, *, status: str, result_summary: Optional[str], session_id: Optional[str]
    ) -> None:
        self._conn.execute(
            """
            UPDATE runs
               SET status = ?, result_summary = ?, session_id = ?, finished_at = datetime('now')
             WHERE id = ?
            """,
            (status, result_summary, session_id, run_id),
        )
        self._conn.commit()

    def get_run(self, run_id: int) -> Optional[Run]:
        row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return Run.from_row(row) if row else None

    def recent_runs(self, limit: int = 20) -> list[Run]:
        rows = self._conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [Run.from_row(r) for r in rows]

    # -- sessions ------------------------------------------------------------

    def get_session_id(self, project_alias: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT session_id FROM sessions WHERE project_alias = ?", (project_alias,)
        ).fetchone()
        return row["session_id"] if row else None

    def set_session_id(self, project_alias: str, session_id: str) -> None:
        self._conn.execute(
            """
            INSERT INTO sessions (project_alias, session_id, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(project_alias) DO UPDATE
                SET session_id = excluded.session_id, updated_at = excluded.updated_at
            """,
            (project_alias, session_id),
        )
        self._conn.commit()

    def clear_session_id(self, project_alias: str) -> None:
        self._conn.execute("DELETE FROM sessions WHERE project_alias = ?", (project_alias,))
        self._conn.commit()
