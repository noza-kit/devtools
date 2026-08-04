import os
from pathlib import Path


def devtoolbox_home() -> Path:
    """Return the devtoolbox data directory, creating it if needed.

    Honors the DEVTOOLBOX_HOME env var so tests (and users) can redirect
    storage away from the real ~/.devtools directory.
    """
    override = os.environ.get("DEVTOOLBOX_HOME")
    home = Path(override) if override else Path.home() / ".devtools"
    home.mkdir(parents=True, exist_ok=True)
    return home


def snippets_db_path() -> Path:
    return devtoolbox_home() / "snippets.db"
