from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

MARKER_FILENAME = ".archived"


@dataclass
class ArchiveMarker:
    archived_at: str
    venv_dir_name: str


def marker_path(project: Path) -> Path:
    return project / MARKER_FILENAME


def is_archived(project: Path) -> bool:
    return marker_path(project).exists()


def write_marker(project: Path, *, venv_dir_name: str) -> ArchiveMarker:
    marker = ArchiveMarker(
        archived_at=datetime.now(timezone.utc).isoformat(),
        venv_dir_name=venv_dir_name,
    )
    marker_path(project).write_text(json.dumps(asdict(marker), indent=2), encoding="utf-8")
    return marker


def read_marker(project: Path) -> Optional[ArchiveMarker]:
    path = marker_path(project)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ArchiveMarker(**data)


def remove_marker(project: Path) -> None:
    marker_path(project).unlink(missing_ok=True)
