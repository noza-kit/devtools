from __future__ import annotations

import pytest

from notify.channels import send_desktop
from notify.exceptions import NotifyError


def test_send_desktop_calls_plyer(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "notify.channels._plyer_notification.notify",
        lambda **kwargs: calls.append(kwargs),
    )

    send_desktop("hello")

    assert calls == [{"title": "Notify", "message": "hello", "app_name": "notify"}]


def test_send_desktop_wraps_backend_exception(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("no display available")

    monkeypatch.setattr("notify.channels._plyer_notification.notify", boom)

    with pytest.raises(NotifyError):
        send_desktop("hello")
