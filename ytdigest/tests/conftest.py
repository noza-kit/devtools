from __future__ import annotations

import pytest

from ytdigest.config import Channels, Secrets, TwitchChannel, YouTubeChannel
from ytdigest.db import Database, Item


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "state.db")
    yield database
    database.close()


@pytest.fixture
def channels():
    return Channels(
        youtube=[YouTubeChannel(channel_id="UCxxxx", name="Example Channel")],
        twitch=[TwitchChannel(login="streamer1", name="Streamer One")],
    )


@pytest.fixture
def secrets():
    return Secrets(
        discord_webhook_new="https://discord.com/api/webhooks/1/new",
        discord_webhook_archive="https://discord.com/api/webhooks/2/archive",
        discord_bot_token="bot-token",
        discord_new_channel_id="555555",
        twitch_client_id="twitch-id",
        twitch_client_secret="twitch-secret",
    )


@pytest.fixture
def no_sleep(monkeypatch):
    """Replace reqretry's time.sleep so retry backoff doesn't actually wait."""
    waits = []
    monkeypatch.setattr("reqretry.session.time.sleep", lambda seconds: waits.append(seconds))
    return waits


@pytest.fixture
def make_item():
    def _make(**overrides) -> Item:
        defaults = dict(
            platform="youtube",
            type="video",
            title="Example Video",
            channel_name="Example Channel",
            url="https://www.youtube.com/watch?v=abc123",
            published_at="2026-08-01T00:00:00Z",
        )
        defaults.update(overrides)
        return Item(**defaults)

    return _make
