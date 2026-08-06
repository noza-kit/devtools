from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from confload import load_config


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class YouTubeChannel:
    channel_id: str
    name: str


@dataclass(frozen=True)
class TwitchChannel:
    login: str
    name: str


@dataclass(frozen=True)
class Channels:
    youtube: list[YouTubeChannel]
    twitch: list[TwitchChannel]


def load_channels(path: str | Path = "channels.yaml") -> Channels:
    config = load_config(path)
    youtube = [
        YouTubeChannel(channel_id=c["channel_id"], name=c.get("name", c["channel_id"]))
        for c in (config.get("youtube") or [])
    ]
    twitch = [
        TwitchChannel(login=c["login"], name=c.get("name", c["login"]))
        for c in (config.get("twitch") or [])
    ]
    return Channels(youtube=youtube, twitch=twitch)


@dataclass(frozen=True)
class Secrets:
    discord_webhook_new: str
    discord_webhook_archive: str
    discord_bot_token: str
    discord_new_channel_id: str
    twitch_client_id: str
    twitch_client_secret: str


# Maps Secrets field name -> required environment variable name.
_ENV_VARS = {
    "discord_webhook_new": "DISCORD_WEBHOOK_NEW",
    "discord_webhook_archive": "DISCORD_WEBHOOK_ARCHIVE",
    "discord_bot_token": "DISCORD_BOT_TOKEN",
    "discord_new_channel_id": "DISCORD_NEW_CHANNEL_ID",
    "twitch_client_id": "TWITCH_CLIENT_ID",
    "twitch_client_secret": "TWITCH_CLIENT_SECRET",
}


def load_secrets(env: Optional[Mapping[str, str]] = None) -> Secrets:
    """Resolve all required secrets from environment variables (GitHub Actions secrets)."""
    env = env if env is not None else os.environ
    values: dict[str, str] = {}
    missing = []
    for field, var in _ENV_VARS.items():
        value = env.get(var)
        if not value:
            missing.append(var)
        else:
            values[field] = value
    if missing:
        raise ConfigError(f"Missing required environment variable(s): {', '.join(missing)}")
    return Secrets(**values)
