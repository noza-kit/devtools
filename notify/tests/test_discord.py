from __future__ import annotations

import json

import pytest
import responses

from notify.channels import send_discord
from notify.exceptions import NotifyConfigError, NotifyError

URL = "https://discord.com/api/webhooks/xxx/yyy"


@responses.activate
def test_send_discord_success(monkeypatch, no_sleep):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", URL)
    responses.add(responses.POST, URL, status=204)

    send_discord("hello")

    assert responses.calls[0].request.url == URL
    assert json.loads(responses.calls[0].request.body) == {"content": "hello"}


def test_send_discord_missing_config_raises(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    with pytest.raises(NotifyConfigError):
        send_discord("hello")


@responses.activate
def test_send_discord_uses_config_object(monkeypatch, no_sleep):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    responses.add(responses.POST, URL, status=204)

    send_discord("hi", config={"discord_webhook_url": URL})

    assert responses.calls[0].request.url == URL


@responses.activate
def test_send_discord_non_2xx_raises_after_retries(monkeypatch, no_sleep):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", URL)
    for _ in range(4):
        responses.add(responses.POST, URL, status=500)

    with pytest.raises(NotifyError):
        send_discord("hello")
