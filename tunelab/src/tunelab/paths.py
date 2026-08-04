from __future__ import annotations

import os
from pathlib import Path


def tunelab_home() -> Path:
    """Config/data directory, overridable via TUNELAB_HOME (mainly for tests)."""
    override = os.environ.get("TUNELAB_HOME")
    path = Path(override) if override else Path.home() / ".tunelab"
    path.mkdir(parents=True, exist_ok=True)
    return path


def studies_dir() -> Path:
    path = tunelab_home() / "studies"
    path.mkdir(parents=True, exist_ok=True)
    return path


def study_db_path(study_name: str) -> Path:
    return studies_dir() / f"{study_name}.db"


def storage_url(study_name: str) -> str:
    return f"sqlite:///{study_db_path(study_name).as_posix()}"


def list_study_names() -> list[str]:
    return sorted(p.stem for p in studies_dir().glob("*.db"))
