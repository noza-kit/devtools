from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from confload import load_config

DEFAULT_TIMEOUT_SECONDS = 1800
DEFAULT_PROGRESS_INTERVAL_SECONDS = 20
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 3600
VALID_MODES = {"diff", "summary"}


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Project:
    alias: str
    path: Path


@dataclass(frozen=True)
class Settings:
    projects: list[Project]
    default_project: Optional[str]
    default_mode: str
    timeout_seconds: int
    progress_interval_seconds: int
    heartbeat_enabled: bool
    heartbeat_interval_seconds: int


def load_settings(path: str | Path) -> Settings:
    """Load the project whitelist + bridge defaults from a YAML/JSON config
    (via confload, so `CLAUDE_BRIDGE_*` env vars can override any key)."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    config = load_config(path, env_prefix="CLAUDE_BRIDGE")

    projects_raw = config.get("projects") or []
    if not projects_raw:
        raise ConfigError(f"No projects registered in {path} (expected a top-level 'projects' list)")

    projects: list[Project] = []
    seen: set[str] = set()
    for i, p in enumerate(projects_raw):
        alias = str(p.get("alias") or "").strip()
        raw_path = p.get("path")
        if not alias:
            raise ConfigError(f"projects[{i}] is missing 'alias'")
        if not raw_path:
            raise ConfigError(f"project {alias!r} is missing 'path'")
        if alias in seen:
            raise ConfigError(f"Duplicate project alias: {alias!r}")
        seen.add(alias)

        resolved = Path(str(raw_path)).expanduser().resolve()
        if not resolved.is_dir():
            raise ConfigError(f"project {alias!r} path does not exist or is not a directory: {resolved}")
        projects.append(Project(alias=alias, path=resolved))

    default_project = config.get("default_project")
    if default_project is not None and default_project not in seen:
        raise ConfigError(f"default_project {default_project!r} is not a registered project alias")

    default_mode = str(config.get("default_mode") or "diff")
    if default_mode not in VALID_MODES:
        raise ConfigError(f"default_mode must be one of {sorted(VALID_MODES)}, got {default_mode!r}")

    heartbeat = config.get("heartbeat") or {}

    return Settings(
        projects=projects,
        default_project=default_project,
        default_mode=default_mode,
        timeout_seconds=int(config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
        progress_interval_seconds=int(
            config.get("progress_interval_seconds", DEFAULT_PROGRESS_INTERVAL_SECONDS)
        ),
        heartbeat_enabled=bool(heartbeat.get("enabled", False)),
        heartbeat_interval_seconds=int(
            heartbeat.get("interval_seconds", DEFAULT_HEARTBEAT_INTERVAL_SECONDS)
        ),
    )


def find_project(settings: Settings, alias: str) -> Optional[Project]:
    for project in settings.projects:
        if project.alias == alias:
            return project
    return None


@dataclass(frozen=True)
class Secrets:
    bot_token: str
    channel_id: str
    allowed_user_ids: frozenset


_ENV_BOT_TOKEN = "CLAUDE_BRIDGE_BOT_TOKEN"
_ENV_CHANNEL_ID = "CLAUDE_BRIDGE_CHANNEL_ID"
_ENV_ALLOWED_USER_IDS = "CLAUDE_BRIDGE_ALLOWED_USER_IDS"


def load_secrets(env: Optional[Mapping[str, str]] = None) -> Secrets:
    """Resolve bot token / channel id / sender allowlist from environment
    variables. Kept separate from load_settings (which reads bridge.yaml):
    these are secrets/deployment-specific, not something to commit to a
    config file."""
    env = env if env is not None else os.environ
    missing = [
        var for var in (_ENV_BOT_TOKEN, _ENV_CHANNEL_ID, _ENV_ALLOWED_USER_IDS) if not env.get(var)
    ]
    if missing:
        raise ConfigError(f"Missing required environment variable(s): {', '.join(missing)}")

    allowed = frozenset(uid.strip() for uid in env[_ENV_ALLOWED_USER_IDS].split(",") if uid.strip())
    if not allowed:
        raise ConfigError(f"{_ENV_ALLOWED_USER_IDS} must contain at least one Discord user id")

    return Secrets(
        bot_token=env[_ENV_BOT_TOKEN],
        channel_id=env[_ENV_CHANNEL_ID],
        allowed_user_ids=allowed,
    )
