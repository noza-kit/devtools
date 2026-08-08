from __future__ import annotations

import os
from pathlib import Path


def projarchive_home() -> Path:
    """Return the directory projarchive stores its metadata DB in, creating it if needed.

    Honors the PROJARCHIVE_HOME env var so tests (and users) can redirect
    storage away from the real ~/.devtools directory.
    """
    override = os.environ.get("PROJARCHIVE_HOME")
    home = Path(override) if override else Path.home() / ".devtools"
    home.mkdir(parents=True, exist_ok=True)
    return home


def compressed_db_path() -> Path:
    return projarchive_home() / "compressed_projects.db"
