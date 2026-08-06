from __future__ import annotations

import os
from pathlib import Path


def sitewatch_home() -> Path:
    """Config/data directory, overridable via SITEWATCH_HOME (mainly for tests)."""
    override = os.environ.get("SITEWATCH_HOME")
    path = Path(override) if override else Path.home() / ".sitewatch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return sitewatch_home() / "sitewatch.db"
