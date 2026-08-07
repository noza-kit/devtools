from __future__ import annotations

import reqretry
import requests

from claude_bridge.config import Secrets

DISCORD_API_BASE = "https://discord.com/api/v10"


class DiscordRestError(Exception):
    pass


def send_ping(secrets: Secrets) -> None:
    """Post a one-shot health-check message via Discord's REST API.

    Reuses the Bot-token-header + reqretry pattern from ytdigest's
    discord_client.py: a full duplex Gateway connection isn't needed just to
    confirm the token/channel id/permissions are valid, so `claude-bridge
    ping` skips straight to a REST call instead of booting the whole bot.
    """
    url = f"{DISCORD_API_BASE}/channels/{secrets.channel_id}/messages"
    try:
        resp = reqretry.post(
            url,
            headers={"Authorization": f"Bot {secrets.bot_token}"},
            json={"content": "\N{TABLE TENNIS PADDLE AND BALL} claude-bridge: ping"},
        )
    except requests.exceptions.RequestException as exc:
        raise DiscordRestError(f"failed to reach Discord: {exc}") from exc

    if not (200 <= resp.status_code < 300):
        raise DiscordRestError(f"Discord returned {resp.status_code}: {resp.text[:200]}")
