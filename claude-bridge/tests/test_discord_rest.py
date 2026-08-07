from __future__ import annotations

import pytest
import responses

from claude_bridge.config import Secrets
from claude_bridge.discord_rest import DISCORD_API_BASE, DiscordRestError, send_ping


@pytest.fixture
def secrets():
    return Secrets(bot_token="my-token", channel_id="777", allowed_user_ids=frozenset({"1"}))


@responses.activate
def test_send_ping_posts_with_bot_authorization(secrets):
    responses.add(
        responses.POST, f"{DISCORD_API_BASE}/channels/777/messages", json={"id": "1"}, status=200
    )

    send_ping(secrets)

    request = responses.calls[0].request
    assert request.headers["Authorization"] == "Bot my-token"


@responses.activate
def test_send_ping_error_status_raises(secrets, no_sleep):
    responses.add(
        responses.POST, f"{DISCORD_API_BASE}/channels/777/messages", status=403, body="forbidden"
    )

    with pytest.raises(DiscordRestError):
        send_ping(secrets)
