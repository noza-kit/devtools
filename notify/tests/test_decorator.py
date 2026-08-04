from __future__ import annotations

import pytest

from notify.decorators import notify_on_complete


def test_notify_on_complete_sends_on_success_and_returns_value(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "notify.decorators.notify",
        lambda msg, channels=None, config=None: sent.append(msg),
    )

    @notify_on_complete("done")
    def work():
        return 42

    assert work() == 42
    assert len(sent) == 1
    assert "done" in sent[0]
    assert "work" in sent[0]


def test_notify_on_complete_notifies_and_reraises_on_error(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "notify.decorators.notify",
        lambda msg, channels=None, config=None: sent.append(msg),
    )

    @notify_on_complete("done")
    def work():
        raise ValueError("bad")

    with pytest.raises(ValueError):
        work()

    assert len(sent) == 1
    assert "failed" in sent[0]
    assert "bad" in sent[0]


def test_notify_on_complete_can_disable_error_notification(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "notify.decorators.notify",
        lambda msg, channels=None, config=None: sent.append(msg),
    )

    @notify_on_complete("done", notify_on_error=False)
    def work():
        raise ValueError("bad")

    with pytest.raises(ValueError):
        work()

    assert sent == []


def test_notify_on_complete_forwards_channels_and_config(monkeypatch):
    received = []
    monkeypatch.setattr(
        "notify.decorators.notify",
        lambda msg, channels=None, config=None: received.append((channels, config)),
    )

    @notify_on_complete("done", channels=["slack", "line"], config={"k": "v"})
    def work():
        pass

    work()

    assert received == [(["slack", "line"], {"k": "v"})]
