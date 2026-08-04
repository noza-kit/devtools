from __future__ import annotations

import json

import pytest
import responses

from notify.channels import LINE_MESSAGE_PUSH_URL, send_line
from notify.exceptions import NotifyConfigError, NotifyError


@responses.activate
def test_send_line_success(monkeypatch, no_sleep):
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok123")
    monkeypatch.setenv("LINE_TO", "U1234567890")
    responses.add(responses.POST, LINE_MESSAGE_PUSH_URL, status=200, json={})

    send_line("hello")

    req = responses.calls[0].request
    assert req.headers["Authorization"] == "Bearer tok123"
    assert json.loads(req.body) == {
        "to": "U1234567890",
        "messages": [{"type": "text", "text": "hello"}],
    }


def test_send_line_missing_token_raises(monkeypatch):
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("LINE_TO", "U1234567890")

    with pytest.raises(NotifyConfigError):
        send_line("hello")


def test_send_line_missing_to_raises(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok123")
    monkeypatch.delenv("LINE_TO", raising=False)

    with pytest.raises(NotifyConfigError):
        send_line("hello")


@responses.activate
def test_send_line_uses_config_object(monkeypatch, no_sleep):
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("LINE_TO", raising=False)
    responses.add(responses.POST, LINE_MESSAGE_PUSH_URL, status=200, json={})

    send_line("hi", config={"line_channel_access_token": "tok456", "line_to": "U999"})

    req = responses.calls[0].request
    assert req.headers["Authorization"] == "Bearer tok456"
    assert json.loads(req.body)["to"] == "U999"


@responses.activate
def test_send_line_non_2xx_raises(monkeypatch, no_sleep):
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok123")
    monkeypatch.setenv("LINE_TO", "U1234567890")
    # 401 isn't in reqretry's default retry_status_codes (5xx only), so no retry.
    responses.add(
        responses.POST,
        LINE_MESSAGE_PUSH_URL,
        status=401,
        json={"message": "Authentication failed"},
    )

    with pytest.raises(NotifyError):
        send_line("hello")

    assert no_sleep == []
