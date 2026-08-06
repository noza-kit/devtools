from __future__ import annotations

import os
from pathlib import Path


def mailwatch_home() -> Path:
    """Config/data directory, overridable via MAILWATCH_HOME (mainly for tests)."""
    override = os.environ.get("MAILWATCH_HOME")
    path = Path(override) if override else Path.home() / ".mailwatch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_credentials_path() -> Path:
    return mailwatch_home() / "credentials.json"


def default_token_path() -> Path:
    return mailwatch_home() / "token.json"


def default_db_path() -> Path:
    return mailwatch_home() / "seen.db"
