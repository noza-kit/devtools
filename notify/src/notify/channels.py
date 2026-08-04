from __future__ import annotations

import os
from typing import Any, Callable, Mapping, Optional

import reqretry
from plyer import notification as _plyer_notification

from notify.exceptions import NotifyConfigError, NotifyError

LINE_MESSAGE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

Config = Optional[Mapping[str, Any]]
ChannelFunc = Callable[..., None]


def _get_setting(name: str, config: Config) -> Optional[str]:
    """Resolve a setting from `config` (dict/confload.Config-like) first, then env vars."""
    if config is not None:
        try:
            value = config[name.lower()]
        except (KeyError, TypeError):
            value = None
        if value is not None:
            return str(value)
    return os.environ.get(name)


def _raise_for_webhook(resp, channel: str) -> None:
    if not (200 <= resp.status_code < 300):
        raise NotifyError(f"{channel} webhook returned {resp.status_code}: {resp.text[:200]}")


def send_slack(message: str, config: Config = None) -> None:
    url = _get_setting("SLACK_WEBHOOK_URL", config)
    if not url:
        raise NotifyConfigError("SLACK_WEBHOOK_URL is not set (env var or config)")
    resp = reqretry.post(url, json={"text": message})
    _raise_for_webhook(resp, "slack")


def send_discord(message: str, config: Config = None) -> None:
    url = _get_setting("DISCORD_WEBHOOK_URL", config)
    if not url:
        raise NotifyConfigError("DISCORD_WEBHOOK_URL is not set (env var or config)")
    resp = reqretry.post(url, json={"content": message})
    _raise_for_webhook(resp, "discord")


def send_line(message: str, config: Config = None) -> None:
    """Push a text message via a LINE Official Account (Messaging API).

    Requires a channel access token (issued for the Official Account in the
    LINE Developers console) and the target user/group/room id to push to -
    LINE Notify, which only needed a token, was discontinued in 2025.
    """
    token = _get_setting("LINE_CHANNEL_ACCESS_TOKEN", config)
    if not token:
        raise NotifyConfigError("LINE_CHANNEL_ACCESS_TOKEN is not set (env var or config)")
    to = _get_setting("LINE_TO", config)
    if not to:
        raise NotifyConfigError("LINE_TO is not set (env var or config)")
    resp = reqretry.post(
        LINE_MESSAGE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": to, "messages": [{"type": "text", "text": message}]},
    )
    _raise_for_webhook(resp, "line")


def send_desktop(message: str, config: Config = None) -> None:
    try:
        _plyer_notification.notify(title="Notify", message=message, app_name="notify")
    except Exception as exc:
        raise NotifyError(f"desktop notification failed: {exc}") from exc


CHANNELS: dict[str, ChannelFunc] = {
    "slack": send_slack,
    "discord": send_discord,
    "line": send_line,
    "desktop": send_desktop,
}
