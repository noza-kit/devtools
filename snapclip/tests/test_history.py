from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from snapclip.history import HistoryStore, filter_entries


def _store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(db_path=tmp_path / "history.db", image_dir=tmp_path / "images")


def test_add_text_and_retrieve(tmp_path: Path):
    with _store(tmp_path) as store:
        entry_id = store.add_text("hello world")
        entry = store.get(entry_id)
        assert entry.kind == "text"
        assert entry.content == "hello world"


def test_add_image_saves_file_and_records_path(tmp_path: Path):
    with _store(tmp_path) as store:
        entry_id = store.add_image(Image.new("RGB", (10, 10)))
        entry = store.get(entry_id)
        assert entry.kind == "image"
        assert Path(entry.content).exists()


def test_all_returns_newest_first(tmp_path: Path):
    with _store(tmp_path) as store:
        store.add_text("first", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        store.add_text("second", now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        entries = store.all()
        assert [e.content for e in entries] == ["second", "first"]


def test_all_respects_limit(tmp_path: Path):
    with _store(tmp_path) as store:
        for i in range(5):
            store.add_text(f"item{i}")
        assert len(store.all(limit=2)) == 2


def test_get_missing_returns_none(tmp_path: Path):
    with _store(tmp_path) as store:
        assert store.get(9999) is None


def test_preview_truncates_long_text(tmp_path: Path):
    with _store(tmp_path) as store:
        store.add_text("x" * 200)
        entry = store.all()[0]
        assert len(entry.preview(max_len=60)) == 60
        assert entry.preview(max_len=60).endswith("…")


def test_preview_image_shows_filename(tmp_path: Path):
    with _store(tmp_path) as store:
        store.add_image(Image.new("RGB", (5, 5)))
        entry = store.all()[0]
        assert entry.preview().startswith("[image]")


def test_filter_entries_case_insensitive_substring(tmp_path: Path):
    with _store(tmp_path) as store:
        store.add_text("Hello World")
        store.add_text("Goodbye")
        entries = store.all()
        assert len(filter_entries(entries, "hello")) == 1
        assert len(filter_entries(entries, "WORLD")) == 1
        assert len(filter_entries(entries, "xyz")) == 0


def test_filter_entries_empty_query_returns_all(tmp_path: Path):
    with _store(tmp_path) as store:
        store.add_text("a")
        store.add_text("b")
        entries = store.all()
        assert len(filter_entries(entries, "")) == 2
