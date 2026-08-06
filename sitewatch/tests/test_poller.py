from __future__ import annotations

import pytest

from sitewatch import poller
from sitewatch.db import add_watch, connect, list_watches
from sitewatch.scraper import ScrapeError, ScrapedContent


class FakeNotify:
    def __init__(self):
        self.calls = []

    def __call__(self, message, channels=None, *, config=None):
        self.calls.append((message, channels, config))
        return {}


@pytest.fixture
def fake_notify(monkeypatch):
    fake = FakeNotify()
    monkeypatch.setattr(poller, "notify", fake)
    return fake


def _content(text: str) -> ScrapedContent:
    return ScrapedContent(text=text, html=f"<div>{text}</div>")


# --- check_watch --------------------------------------------------------------------


def test_check_watch_first_check_records_baseline_without_notifying(tmp_path, monkeypatch, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, url="https://example.test/x", selector="#price", name="Example")
        monkeypatch.setattr(poller, "scrape_selector", lambda url, selector: _content("$9.99"))

        changed = poller.check_watch(conn, watch, channels=["desktop"])

        assert changed is False
        assert fake_notify.calls == []
        assert list_watches(conn)[0].last_hash == _content("$9.99").content_hash


def test_check_watch_notifies_on_change(tmp_path, monkeypatch, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, url="https://example.test/x", selector="#price", name="Example")
        monkeypatch.setattr(poller, "scrape_selector", lambda url, selector: _content("$9.99"))
        poller.check_watch(conn, watch, channels=["desktop"])

        watch = list_watches(conn)[0]
        monkeypatch.setattr(poller, "scrape_selector", lambda url, selector: _content("$8.99"))
        changed = poller.check_watch(conn, watch, channels=["desktop"])

        assert changed is True
        assert len(fake_notify.calls) == 1
        assert "Example" in fake_notify.calls[0][0]
        assert watch.url in fake_notify.calls[0][0]


def test_check_watch_no_notify_when_unchanged(tmp_path, monkeypatch, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, url="https://example.test/x", selector="#price", name="Example")
        monkeypatch.setattr(poller, "scrape_selector", lambda url, selector: _content("$9.99"))
        poller.check_watch(conn, watch, channels=["desktop"])

        watch = list_watches(conn)[0]
        changed = poller.check_watch(conn, watch, channels=["desktop"])

        assert changed is False
        assert fake_notify.calls == []


def test_check_watch_scrape_error_is_swallowed(tmp_path, monkeypatch, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, url="https://example.test/x", selector="#price", name="Example")

        def _raise(url, selector):
            raise ScrapeError("boom")

        monkeypatch.setattr(poller, "scrape_selector", _raise)

        changed = poller.check_watch(conn, watch, channels=["desktop"])

        assert changed is False
        assert fake_notify.calls == []


# --- check_all: respects per-watch min interval --------------------------------------


def test_check_all_skips_watches_not_yet_due(tmp_path, monkeypatch, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(
            conn, url="https://example.test/x", selector="#price", name="Example", min_interval_sec=1800
        )
        monkeypatch.setattr(poller, "scrape_selector", lambda url, selector: _content("$9.99"))

        # First pass: never checked -> due -> baseline recorded.
        poller.check_all(conn, channels=["desktop"])
        calls_after_first = len(fake_notify.calls)

        # Second pass immediately after: not due yet (min_interval_sec=1800) -> skipped entirely.
        monkeypatch.setattr(poller, "scrape_selector", lambda url, selector: _content("$8.99"))
        changed_count = poller.check_all(conn, channels=["desktop"])

        assert changed_count == 0
        assert len(fake_notify.calls) == calls_after_first


# --- run_forever ----------------------------------------------------------------------


def test_run_forever_sleeps_between_cycles_but_not_after_the_last(sitewatch_home, monkeypatch, fake_notify):
    sleeps = []
    monkeypatch.setattr(poller.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(poller, "scrape_selector", lambda url, selector: _content("x"))

    poller.run_forever(interval_seconds=5, channels=["desktop"], max_cycles=3)

    assert sleeps == [5, 5]
