from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Compression:
    id: int
    project_name: str
    parent_dir: str
    archive_path: str
    format: str
    compression_level: str
    compressed_at: str
    original_size_bytes: int
    compressed_size_bytes: int
    venv_stripped: bool
    venv_dir_name: Optional[str]
    excluded_files: list[dict]
    excluded_dir: Optional[str]
    status: str
    restored_at: Optional[str]
    restore_elapsed_seconds: Optional[float]
    restore_venv_rebuilt: Optional[bool]
    restore_used_uv: Optional[bool]


def _row_to_compression(row: sqlite3.Row) -> Compression:
    return Compression(
        id=row["id"],
        project_name=row["project_name"],
        parent_dir=row["parent_dir"],
        archive_path=row["archive_path"],
        format=row["format"],
        compression_level=row["compression_level"],
        compressed_at=row["compressed_at"],
        original_size_bytes=row["original_size_bytes"],
        compressed_size_bytes=row["compressed_size_bytes"],
        venv_stripped=bool(row["venv_stripped"]),
        venv_dir_name=row["venv_dir_name"],
        excluded_files=json.loads(row["excluded_files"]),
        excluded_dir=row["excluded_dir"],
        status=row["status"],
        restored_at=row["restored_at"],
        restore_elapsed_seconds=row["restore_elapsed_seconds"],
        restore_venv_rebuilt=None if row["restore_venv_rebuilt"] is None else bool(row["restore_venv_rebuilt"]),
        restore_used_uv=None if row["restore_used_uv"] is None else bool(row["restore_used_uv"]),
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
        CREATE TABLE IF NOT EXISTS compressions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            parent_dir TEXT NOT NULL,
            archive_path TEXT NOT NULL,
            format TEXT NOT NULL,
            compression_level TEXT NOT NULL,
            compressed_at TEXT NOT NULL,
            original_size_bytes INTEGER NOT NULL,
            compressed_size_bytes INTEGER NOT NULL,
            venv_stripped INTEGER NOT NULL DEFAULT 0,
            venv_dir_name TEXT,
            excluded_files TEXT NOT NULL DEFAULT '[]',
            excluded_dir TEXT,
            status TEXT NOT NULL DEFAULT 'compressed',
            restored_at TEXT,
            restore_elapsed_seconds REAL,
            restore_venv_rebuilt INTEGER,
            restore_used_uv INTEGER
        )
        """
    )
    conn.commit()


def insert_compression(
    conn: sqlite3.Connection,
    *,
    project_name: str,
    parent_dir: str,
    archive_path: str,
    format: str,
    compression_level: str,
    original_size_bytes: int,
    compressed_size_bytes: int,
    venv_stripped: bool,
    venv_dir_name: Optional[str],
    excluded_files: list[dict],
    excluded_dir: Optional[str],
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO compressions (
            project_name, parent_dir, archive_path, format, compression_level,
            compressed_at, original_size_bytes, compressed_size_bytes,
            venv_stripped, venv_dir_name, excluded_files, excluded_dir, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'compressed')
        """,
        (
            project_name,
            parent_dir,
            archive_path,
            format,
            compression_level,
            now,
            original_size_bytes,
            compressed_size_bytes,
            int(venv_stripped),
            venv_dir_name,
            json.dumps(excluded_files, ensure_ascii=False),
            excluded_dir,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def mark_restored(
    conn: sqlite3.Connection,
    compression_id: int,
    *,
    elapsed_seconds: float,
    venv_rebuilt: Optional[bool],
    used_uv: Optional[bool],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE compressions
        SET status = 'restored', restored_at = ?, restore_elapsed_seconds = ?,
            restore_venv_rebuilt = ?, restore_used_uv = ?
        WHERE id = ?
        """,
        (
            now,
            elapsed_seconds,
            None if venv_rebuilt is None else int(venv_rebuilt),
            None if used_uv is None else int(used_uv),
            compression_id,
        ),
    )
    conn.commit()


def get_by_archive_path(conn: sqlite3.Connection, archive_path: str) -> Optional[Compression]:
    row = conn.execute(
        "SELECT * FROM compressions WHERE archive_path = ? ORDER BY id DESC LIMIT 1",
        (archive_path,),
    ).fetchone()
    return _row_to_compression(row) if row else None


def list_active_compressions(conn: sqlite3.Connection, parent_dir: str) -> list[Compression]:
    """Compressed-but-not-yet-restored records under PARENT_DIR, most recent first."""
    rows = conn.execute(
        "SELECT * FROM compressions WHERE parent_dir = ? AND status = 'compressed' ORDER BY id DESC",
        (parent_dir,),
    ).fetchall()
    return [_row_to_compression(r) for r in rows]
