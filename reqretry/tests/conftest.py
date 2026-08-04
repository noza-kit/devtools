from __future__ import annotations

import pytest

import reqretry
from reqretry import RetryConfig, Session


@pytest.fixture
def no_sleep(monkeypatch):
    """Replace time.sleep with a recorder so tests don't actually wait out the backoff."""
    waits = []
    monkeypatch.setattr("reqretry.session.time.sleep", lambda seconds: waits.append(seconds))
    return waits


@pytest.fixture
def session(no_sleep) -> Session:
    return Session(RetryConfig())


@pytest.fixture(autouse=True)
def reset_default_session():
    """Module-level get/post/etc. share one Session; restore its config after each test."""
    original = reqretry.get_default_session().retry_config
    yield
    reqretry.get_default_session().retry_config = original
