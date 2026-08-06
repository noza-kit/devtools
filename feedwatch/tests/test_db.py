from __future__ import annotations

import pytest

from feedwatch.db import (
    DuplicateWatchError,
    WatchNotFoundError,
    add_watch,
    connect,
    has_seen,
    list_watches,
    mark_seen,
    remove_watch,
)


def test_add_and_list_watch(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="rss", source="https://example.test/feed.xml", name="Example", tags=["youtube"])
        assert watch.id == 1
        assert watch.kind == "rss"
        assert watch.tag_list == ["youtube"]

    with connect(db) as conn:
        watches = list_watches(conn)
        assert len(watches) == 1
        assert watches[0].name == "Example"


def test_list_watches_filters_by_kind(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        add_watch(conn, kind="rss", source="https://example.test/feed.xml", name="RSS one", tags=[])
        add_watch(conn, kind="twitch", source="somestreamer", name="Streamer", tags=[])

        assert [w.kind for w in list_watches(conn, kind="rss")] == ["rss"]
        assert [w.kind for w in list_watches(conn, kind="twitch")] == ["twitch"]
        assert len(list_watches(conn)) == 2


def test_add_duplicate_source_raises(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        add_watch(conn, kind="rss", source="https://example.test/feed.xml", name="Example", tags=[])
        with pytest.raises(DuplicateWatchError):
            add_watch(conn, kind="rss", source="https://example.test/feed.xml", name="Example2", tags=[])


def test_same_source_different_kind_is_allowed(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        add_watch(conn, kind="rss", source="samevalue", name="A", tags=[])
        # Different kind -> not a UNIQUE(kind, source) collision
        add_watch(conn, kind="twitch", source="samevalue", name="B", tags=[])
        assert len(list_watches(conn)) == 2


def test_remove_watch(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="rss", source="https://example.test/feed.xml", name="Example", tags=[])
        remove_watch(conn, watch.id)
        assert list_watches(conn) == []


def test_remove_missing_watch_raises(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        with pytest.raises(WatchNotFoundError):
            remove_watch(conn, 999)


def test_seen_items_dedupe(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="rss", source="https://example.test/feed.xml", name="Example", tags=[])

        assert not has_seen(conn, watch.id, "item1")
        mark_seen(conn, watch.id, "item1")
        assert has_seen(conn, watch.id, "item1")

        # marking the same item again must not raise (INSERT OR IGNORE)
        mark_seen(conn, watch.id, "item1")
        assert has_seen(conn, watch.id, "item1")
        assert not has_seen(conn, watch.id, "item2")


def test_remove_watch_cascades_seen_items(tmp_path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="rss", source="https://example.test/feed.xml", name="Example", tags=[])
        mark_seen(conn, watch.id, "item1")
        remove_watch(conn, watch.id)

    with connect(db) as conn:
        rows = conn.execute("SELECT * FROM seen_items").fetchall()
        assert rows == []
