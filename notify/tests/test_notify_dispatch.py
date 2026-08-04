from __future__ import annotations

import pytest

from notify.channels import CHANNELS
from notify.core import notify
from notify.exceptions import NotifyError


def test_notify_dispatches_to_multiple_channels(monkeypatch):
    calls = []
    monkeypatch.setitem(CHANNELS, "ok_channel", lambda msg, config=None: calls.append(msg))

    def failing(msg, config=None):
        raise NotifyError("boom")

    monkeypatch.setitem(CHANNELS, "fail_channel", failing)

    results = notify("hi", ["ok_channel", "fail_channel"])

    assert calls == ["hi"]
    assert results["ok_channel"].ok is True
    assert results["ok_channel"].error is None
    assert results["fail_channel"].ok is False
    assert "boom" in results["fail_channel"].error


def test_notify_unknown_channel_is_recorded_not_raised():
    results = notify("hi", ["nonexistent"])

    assert results["nonexistent"].ok is False
    assert "unknown channel" in results["nonexistent"].error


def test_notify_default_channel_is_desktop(monkeypatch):
    calls = []
    monkeypatch.setitem(CHANNELS, "desktop", lambda msg, config=None: calls.append(msg))

    results = notify("hi")

    assert calls == ["hi"]
    assert results["desktop"].ok is True


def test_notify_passes_config_through_to_handler(monkeypatch):
    received = []
    monkeypatch.setitem(
        CHANNELS, "cfg_channel", lambda msg, config=None: received.append(config)
    )

    notify("hi", ["cfg_channel"], config={"some_key": "value"})

    assert received == [{"some_key": "value"}]
