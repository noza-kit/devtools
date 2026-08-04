from __future__ import annotations

import json

import pytest
import responses

from notify.channels import send_slack
from notify.exceptions import NotifyConfigError, NotifyError

URL = "https://hooks.slack.com/services/xxx"


@responses.activate
def test_send_slack_success(monkeypatch, no_sleep):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", URL)
    responses.add(responses.POST, URL, status=200, body="ok")

    send_slack("hello")

    assert responses.calls[0].request.url == URL
    assert json.loads(responses.calls[0].request.body) == {"text": "hello"}


def test_send_slack_missing_config_raises(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    with pytest.raises(NotifyConfigError):
        send_slack("hello")


@responses.activate
def test_send_slack_uses_config_object(monkeypatch, no_sleep):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    responses.add(responses.POST, URL, status=200)

    send_slack("hi", config={"slack_webhook_url": URL})

    assert responses.calls[0].request.url == URL


@responses.activate
def test_send_slack_non_2xx_raises_after_retries(monkeypatch, no_sleep):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", URL)
    for _ in range(4):  # reqretry default: 1 initial attempt + 3 retries, all 500
        responses.add(responses.POST, URL, status=500)

    with pytest.raises(NotifyError):
        send_slack("hello")

    assert no_sleep == [1.0, 2.0, 4.0]
