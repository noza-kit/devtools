from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sitewatch.db import (
    DuplicateWatchError,
    WatchNotFoundError,
    add_watch,
    connect,
    is_due,
    list_watches,
    record_check,
    remove_watch,
)


def test_add_and_list_watch(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(conn, url="https://example.test/x", selector="#price", name="Example")
        assert watch.id == 1
        assert watch.min_interval_sec == 1800
        assert watch.last_hash is None

    with connect(db) as conn:
        watches = list_watches(conn)
        assert len(watches) == 1
        assert watches[0].name == "Example"


def test_add_with_custom_min_interval(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(conn, url="https://example.test/x", selector="#price", name="Example", min_interval_sec=60)
        assert watch.min_interval_sec == 60


def test_add_duplicate_url_selector_raises(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        add_watch(conn, url="https://example.test/x", selector="#price", name="Example")
        with pytest.raises(DuplicateWatchError):
            add_watch(conn, url="https://example.test/x", selector="#price", name="Example2")


def test_same_url_different_selector_is_allowed(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        add_watch(conn, url="https://example.test/x", selector="#price", name="Price")
        add_watch(conn, url="https://example.test/x", selector="#stock", name="Stock")
        assert len(list_watches(conn)) == 2


def test_remove_watch(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(conn, url="https://example.test/x", selector="#price", name="Example")
        remove_watch(conn, watch.id)
        assert list_watches(conn) == []


def test_remove_missing_watch_raises(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        with pytest.raises(WatchNotFoundError):
            remove_watch(conn, 999)


def test_record_check_updates_hash_and_timestamp(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(conn, url="https://example.test/x", selector="#price", name="Example")
        record_check(conn, watch.id, "abc123")

        rows = conn.execute("SELECT last_hash, last_checked_at FROM watches WHERE id = ?", (watch.id,)).fetchall()
        assert rows[0]["last_hash"] == "abc123"
        assert rows[0]["last_checked_at"] is not None


# --- is_due ------------------------------------------------------------------------


def test_is_due_true_when_never_checked(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(conn, url="https://example.test/x", selector="#price", name="Example")
    assert is_due(watch) is True


def test_is_due_false_within_min_interval(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(
            conn, url="https://example.test/x", selector="#price", name="Example", min_interval_sec=1800
        )
        record_check(conn, watch.id, "abc123")
        watch = list_watches(conn)[0]

    now = datetime.fromisoformat(watch.last_checked_at) + timedelta(seconds=100)
    assert is_due(watch, now=now) is False


def test_is_due_true_after_min_interval_elapses(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(
            conn, url="https://example.test/x", selector="#price", name="Example", min_interval_sec=1800
        )
        record_check(conn, watch.id, "abc123")
        watch = list_watches(conn)[0]

    now = datetime.fromisoformat(watch.last_checked_at) + timedelta(seconds=1800)
    assert is_due(watch, now=now) is True
