from pathlib import Path

from notesearch.chunking import Chunk
from notesearch.config import Settings
from notesearch.sync import clean_index, sync_index


class FakeIndexStore:
    """In-memory stand-in for VectorStore, so sync/clean logic is
    tested independently of ChromaDB/embeddings."""

    def __init__(self):
        self.documents: dict[str, tuple[list[Chunk], float]] = {}
        self.upsert_calls: list[str] = []

    def get_indexed_sources(self) -> dict[str, float]:
        return {source: mtime for source, (_, mtime) in self.documents.items()}

    def upsert_document(self, source: str, chunks: list[Chunk], mtime: float) -> None:
        self.documents[source] = (chunks, mtime)
        self.upsert_calls.append(source)

    def delete_document(self, source: str) -> None:
        self.documents.pop(source, None)


def _write(path: Path, text: str = "# Heading\nBody text") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_sync_index_adds_new_files(tmp_path: Path):
    _write(tmp_path / "a.md")
    _write(tmp_path / "b.md")
    store = FakeIndexStore()
    settings = Settings(target_dirs=[tmp_path])

    report = sync_index(store, settings)

    assert report.added == 2
    assert report.updated == 0
    assert report.unchanged == 0
    assert len(store.documents) == 2


def test_sync_index_second_run_is_all_unchanged(tmp_path: Path):
    _write(tmp_path / "a.md")
    store = FakeIndexStore()
    settings = Settings(target_dirs=[tmp_path])

    sync_index(store, settings)
    report = sync_index(store, settings)

    assert report.added == 0
    assert report.unchanged == 1
    assert store.upsert_calls == [str(tmp_path / "a.md")]  # only embedded once


def test_sync_index_detects_modified_file(tmp_path: Path):
    path = tmp_path / "a.md"
    _write(path, "original content")
    store = FakeIndexStore()
    settings = Settings(target_dirs=[tmp_path])
    sync_index(store, settings)

    import time

    time.sleep(0.01)
    path.write_text("changed content", encoding="utf-8")
    # force a newer mtime explicitly, in case the filesystem's mtime resolution is coarse
    import os

    os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 1))

    report = sync_index(store, settings)
    assert report.updated == 1
    assert report.unchanged == 0


def test_sync_index_report_changed_property(tmp_path: Path):
    _write(tmp_path / "a.md")
    store = FakeIndexStore()
    report = sync_index(store, Settings(target_dirs=[tmp_path]))
    assert report.changed == 1


def test_sync_index_respects_exclude(tmp_path: Path):
    _write(tmp_path / "venv" / "note.md")
    _write(tmp_path / "real.md")
    store = FakeIndexStore()
    settings = Settings(target_dirs=[tmp_path], exclude=["venv"])
    report = sync_index(store, settings)
    assert report.added == 1


def test_clean_index_removes_deleted_files(tmp_path: Path):
    path = tmp_path / "a.md"
    _write(path)
    store = FakeIndexStore()
    settings = Settings(target_dirs=[tmp_path])
    sync_index(store, settings)

    path.unlink()
    report = clean_index(store)

    assert report.removed == 1
    assert store.documents == {}


def test_clean_index_keeps_existing_files(tmp_path: Path):
    _write(tmp_path / "a.md")
    store = FakeIndexStore()
    settings = Settings(target_dirs=[tmp_path])
    sync_index(store, settings)

    report = clean_index(store)
    assert report.removed == 0
    assert len(store.documents) == 1
