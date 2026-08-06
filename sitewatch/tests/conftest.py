from __future__ import annotations

import pytest


@pytest.fixture
def no_sleep(monkeypatch):
    """Replace reqretry's time.sleep so retry backoff doesn't actually wait."""
    waits = []
    monkeypatch.setattr("reqretry.session.time.sleep", lambda seconds: waits.append(seconds))
    return waits


@pytest.fixture
def sitewatch_home(tmp_path, monkeypatch):
    """Isolate sitewatch's SQLite db (~/.sitewatch) to a temp directory for each test."""
    monkeypatch.setenv("SITEWATCH_HOME", str(tmp_path))
    return tmp_path
