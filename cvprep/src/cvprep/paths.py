from __future__ import annotations

import os
from pathlib import Path


def cvprep_home() -> Path:
    """Config/data directory, overridable via CVPREP_HOME (mainly for tests)."""
    override = os.environ.get("CVPREP_HOME")
    path = Path(override) if override else Path.home() / ".cvprep"
    path.mkdir(parents=True, exist_ok=True)
    return path


def presets_path() -> Path:
    return cvprep_home() / "presets.yaml"
