from __future__ import annotations

from mailwatch.store import SeenStore


def test_seen_store_dedup(tmp_path):
    with SeenStore(tmp_path / "seen.db") as store:
        assert not store.is_seen("msg1")

        store.mark_seen("msg1", ["rule-a"])

        assert store.is_seen("msg1")
        assert not store.is_seen("msg2")


def test_seen_store_persists_across_instances(tmp_path):
    db_path = tmp_path / "seen.db"

    with SeenStore(db_path) as store:
        store.mark_seen("msg1", [])

    with SeenStore(db_path) as store:
        assert store.is_seen("msg1")


def test_seen_store_mark_seen_is_idempotent(tmp_path):
    with SeenStore(tmp_path / "seen.db") as store:
        store.mark_seen("msg1", ["rule-a"])
        store.mark_seen("msg1", ["rule-a"])  # should not raise (INSERT OR IGNORE)

        assert store.is_seen("msg1")
