from __future__ import annotations

import os
from pathlib import Path


def feedwatch_home() -> Path:
    """Config/data directory, overridable via FEEDWATCH_HOME (mainly for tests)."""
    override = os.environ.get("FEEDWATCH_HOME")
    path = Path(override) if override else Path.home() / ".feedwatch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return feedwatch_home() / "feedwatch.db"
