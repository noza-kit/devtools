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


def todo_db_path() -> Path:
    return devtoolbox_home() / "todo.db"


def dotsync_home() -> Path:
    """Directory dotsync treats as $HOME. Overridable via DOTSYNC_HOME (used by tests)."""
    override = os.environ.get("DOTSYNC_HOME")
    return Path(override) if override else Path.home()


def orgdir_log_path() -> Path:
    return devtoolbox_home() / "orgdir.log"
