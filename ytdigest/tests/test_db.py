from __future__ import annotations


def test_add_item_returns_id(db, make_item):
    item_id = db.add_item(make_item())
    assert item_id is not None

    stored = db.get_item(item_id)
    assert stored.title == "Example Video"
    assert stored.status == "pending"


def test_add_item_duplicate_url_is_noop(db, make_item):
    first_id = db.add_item(make_item())
    second_id = db.add_item(make_item(title="Different Title"))

    assert second_id is None
    assert db.get_item(first_id).title == "Example Video"


def test_get_item_by_url(db, make_item):
    db.add_item(make_item())
    found = db.get_item_by_url("https://www.youtube.com/watch?v=abc123")
    assert found is not None
    assert found.title == "Example Video"


def test_get_item_by_url_missing_returns_none(db):
    assert db.get_item_by_url("https://example.com/missing") is None


def test_get_items_by_status(db, make_item):
    db.add_item(make_item(url="https://youtube.com/1"))
    db.add_item(make_item(url="https://youtube.com/2"))
    id3 = db.add_item(make_item(url="https://youtube.com/3"))
    db.set_status(id3, "dismissed")

    pending = db.get_items_by_status("pending")
    dismissed = db.get_items_by_status("dismissed")

    assert len(pending) == 2
    assert len(dismissed) == 1
    assert dismissed[0].id == id3


def test_set_status(db, make_item):
    item_id = db.add_item(make_item())
    db.set_status(item_id, "archived")

    assert db.get_item(item_id).status == "archived"


def test_mark_notified_and_lookup_by_notify(db, make_item):
    item_id = db.add_item(make_item())
    db.mark_notified(item_id, message_id="msg-1", number=2, notified_at="2026-08-01T12:00:00Z")

    found = db.get_item_by_notify("msg-1", 2)
    assert found is not None
    assert found.id == item_id
    assert found.notified_at == "2026-08-01T12:00:00Z"

    assert db.get_item_by_notify("msg-1", 3) is None
    assert db.get_item_by_notify("msg-2", 2) is None


def test_get_stale_pending_items_excludes_recent_and_non_pending(db, make_item):
    stale_id = db.add_item(make_item(url="https://youtube.com/stale"))
    db.mark_notified(stale_id, message_id="m1", number=1, notified_at="2026-08-01T00:00:00Z")

    recent_id = db.add_item(make_item(url="https://youtube.com/recent"))
    db.mark_notified(recent_id, message_id="m2", number=1, notified_at="2026-08-05T00:00:00Z")

    not_notified_id = db.add_item(make_item(url="https://youtube.com/not-notified"))

    archived_id = db.add_item(make_item(url="https://youtube.com/archived"))
    db.mark_notified(archived_id, message_id="m3", number=1, notified_at="2026-08-01T00:00:00Z")
    db.set_status(archived_id, "archived")

    stale = db.get_stale_pending_items(cutoff="2026-08-03T00:00:00Z")

    assert [item.id for item in stale] == [stale_id]
    assert not_notified_id not in [item.id for item in stale]


def test_get_stale_pending_items_excludes_live_tracked(db, make_item):
    live_id = db.add_item(make_item(url="https://twitch.tv/live1", platform="twitch", type="live"))
    db.mark_notified(live_id, message_id="m1", number=1, notified_at="2026-08-01T00:00:00Z")
    db.add_live_tracking("streamer1", live_id, "2026-08-01T00:00:00Z")

    stale = db.get_stale_pending_items(cutoff="2026-08-03T00:00:00Z")

    assert stale == []


def test_live_tracking_crud(db, make_item):
    item_id = db.add_item(make_item(url="https://twitch.tv/live1", platform="twitch", type="live"))
    db.add_live_tracking("streamer1", item_id, "2026-08-01T00:00:00Z")

    found = db.get_live_tracking("streamer1")
    assert found is not None
    assert found.item_id == item_id

    all_tracking = db.list_live_tracking()
    assert len(all_tracking) == 1

    db.remove_live_tracking("streamer1")
    assert db.get_live_tracking("streamer1") is None
    assert db.list_live_tracking() == []


def test_meta_get_set(db):
    assert db.get_meta("last_seen_message_id") is None

    db.set_meta("last_seen_message_id", "12345")
    assert db.get_meta("last_seen_message_id") == "12345"

    db.set_meta("last_seen_message_id", "67890")
    assert db.get_meta("last_seen_message_id") == "67890"


def test_reopening_existing_db_preserves_data(tmp_path, make_item):
    from ytdigest.db import Database

    path = tmp_path / "state.db"
    db1 = Database(path)
    item_id = db1.add_item(make_item())
    db1.close()

    db2 = Database(path)
    try:
        assert db2.get_item(item_id).title == "Example Video"
    finally:
        db2.close()
