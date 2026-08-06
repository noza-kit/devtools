from __future__ import annotations

import pytest


@pytest.fixture
def no_sleep(monkeypatch):
    """Replace reqretry's time.sleep so retry backoff doesn't actually wait."""
    waits = []
    monkeypatch.setattr("reqretry.session.time.sleep", lambda seconds: waits.append(seconds))
    return waits


@pytest.fixture
def feedwatch_home(tmp_path, monkeypatch):
    """Isolate feedwatch's SQLite db (~/.feedwatch) to a temp directory for each test."""
    monkeypatch.setenv("FEEDWATCH_HOME", str(tmp_path))
    return tmp_path
