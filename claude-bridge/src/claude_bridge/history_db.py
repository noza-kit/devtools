from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_alias TEXT NOT NULL,
    user_id TEXT NOT NULL,
    instruction TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('diff', 'summary')),
    status TEXT NOT NULL
        CHECK (status IN ('running', 'completed', 'failed', 'timeout', 'cancelled')),
    result_summary TEXT,
    session_id TEXT,
    total_cost_usd REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_creation_input_tokens INTEGER,
    cache_read_input_tokens INTEGER,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_alias);

CREATE TABLE IF NOT EXISTS sessions (
    project_alias TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# Added after the initial release; applied via ALTER TABLE for DBs created
# before these columns existed (CREATE TABLE IF NOT EXISTS above only
# affects brand-new files).
_MIGRATED_RUN_COLUMNS = {
    "total_cost_usd": "REAL",
    "input_tokens": "INTEGER",
    "output_tokens": "INTEGER",
    "cache_creation_input_tokens": "INTEGER",
    "cache_read_input_tokens": "INTEGER",
}


@dataclass
class Run:
    project_alias: str
    user_id: str
    instruction: str
    mode: str
    status: str = "running"
    result_summary: Optional[str] = None
    session_id: Optional[str] = None
    total_cost_usd: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None
    id: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Run":
        return cls(**{k: row[k] for k in row.keys()})


@dataclass
class UsageSummary:
    run_count: int
    total_cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


@dataclass
class ProjectUsage:
    project_alias: str
    run_count: int
    total_cost_usd: float


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
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Add columns introduced after the initial release to DBs created
        before them existed (CREATE TABLE IF NOT EXISTS in SCHEMA only
        affects brand-new files)."""
        existing = {row["name"] for row in self._conn.execute("PRAGMA table_info(runs)")}
        for column, coltype in _MIGRATED_RUN_COLUMNS.items():
            if column not in existing:
                self._conn.execute(f"ALTER TABLE runs ADD COLUMN {column} {coltype}")

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
        self,
        run_id: int,
        *,
        status: str,
        result_summary: Optional[str],
        session_id: Optional[str],
        total_cost_usd: Optional[float] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cache_creation_input_tokens: Optional[int] = None,
        cache_read_input_tokens: Optional[int] = None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE runs
               SET status = ?, result_summary = ?, session_id = ?,
                   total_cost_usd = ?, input_tokens = ?, output_tokens = ?,
                   cache_creation_input_tokens = ?, cache_read_input_tokens = ?,
                   finished_at = datetime('now')
             WHERE id = ?
            """,
            (
                status,
                result_summary,
                session_id,
                total_cost_usd,
                input_tokens,
                output_tokens,
                cache_creation_input_tokens,
                cache_read_input_tokens,
                run_id,
            ),
        )
        self._conn.commit()

    def get_run(self, run_id: int) -> Optional[Run]:
        row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return Run.from_row(row) if row else None

    def recent_runs(self, limit: int = 20) -> list[Run]:
        rows = self._conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [Run.from_row(r) for r in rows]

    # -- usage -----------------------------------------------------------------

    def usage_summary(self, *, since_days: Optional[int] = None) -> UsageSummary:
        """Aggregate cost/token totals across all runs, or only runs started
        within the last `since_days` days."""
        where, params = self._since_clause(since_days)
        row = self._conn.execute(
            f"""
            SELECT
                COUNT(*) AS run_count,
                COALESCE(SUM(total_cost_usd), 0) AS total_cost_usd,
                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                COALESCE(SUM(cache_creation_input_tokens), 0) AS cache_creation_input_tokens,
                COALESCE(SUM(cache_read_input_tokens), 0) AS cache_read_input_tokens
            FROM runs
            {where}
            """,
            params,
        ).fetchone()
        return UsageSummary(**{k: row[k] for k in row.keys()})

    def usage_by_project(self, *, since_days: Optional[int] = None) -> list[ProjectUsage]:
        where, params = self._since_clause(since_days)
        rows = self._conn.execute(
            f"""
            SELECT project_alias, COUNT(*) AS run_count, COALESCE(SUM(total_cost_usd), 0) AS total_cost_usd
            FROM runs
            {where}
            GROUP BY project_alias
            ORDER BY total_cost_usd DESC
            """,
            params,
        ).fetchall()
        return [
            ProjectUsage(project_alias=r["project_alias"], run_count=r["run_count"], total_cost_usd=r["total_cost_usd"])
            for r in rows
        ]

    @staticmethod
    def _since_clause(since_days: Optional[int]) -> tuple[str, tuple]:
        if since_days is None:
            return "", ()
        return "WHERE started_at >= datetime('now', ?)", (f"-{since_days} days",)

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
