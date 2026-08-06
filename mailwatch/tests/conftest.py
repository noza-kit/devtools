from __future__ import annotations

import pytest


@pytest.fixture
def no_sleep(monkeypatch):
    """Replace reqretry's time.sleep so retry backoff doesn't actually wait."""
    waits = []
    monkeypatch.setattr("reqretry.session.time.sleep", lambda seconds: waits.append(seconds))
    return waits
