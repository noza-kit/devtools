from pathlib import Path

from notesearch.config import Settings
from notesearch.search import build_where_clause, search


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_where_clause_none_when_no_filters():
    assert build_where_clause() is None


def test_build_where_clause_directory_only():
    assert build_where_clause(directory="proj_a") == {"directory": "proj_a"}


def test_build_where_clause_days_only():
    clause = build_where_clause(since_days=30, now=1000000.0)
    assert clause == {"last_modified": {"$gte": 1000000.0 - 30 * 86400}}


def test_build_where_clause_both_combines_with_and():
    clause = build_where_clause(directory="proj_a", since_days=30, now=1000000.0)
    assert clause == {"$and": [{"directory": "proj_a"}, {"last_modified": {"$gte": 1000000.0 - 30 * 86400}}]}


def test_search_finds_keyword_match_via_bm25(tmp_path: Path, fake_embedder):
    # fake_embedder's hash-based "vectors" carry no real semantic
    # signal, so this test leans on BM25 to make the ranking
    # deterministic -- which itself needs a corpus that isn't tiny (see
    # test_bm25index.py's note on 2-document corpora giving a shared
    # term a degenerate negative IDF), hence the filler documents.
    from notesearch.vectordb import VectorStore

    _write(tmp_path / "docker.md", "# Docker\nRebuild the image with docker build --no-cache to fix cache issues.")
    _write(tmp_path / "nginx.md", "# Nginx\nConfigure a reverse proxy with proxy_pass.")
    _write(tmp_path / "cooking.md", "# Recipe\nA recipe for chocolate cake and cookies.")
    _write(tmp_path / "garden.md", "# Garden\nTips for growing tomatoes in spring.")

    settings = Settings(target_dirs=[tmp_path], db_dir=tmp_path / "db")
    store = VectorStore(settings.db_dir, fake_embedder)

    results, report = search("docker build cache", store, settings, top_k=5)

    assert report.added == 4
    assert results
    assert "docker.md" in results[0].metadata["source"]


def test_search_second_call_does_not_resync_unchanged_files(tmp_path: Path, fake_embedder):
    from notesearch.vectordb import VectorStore

    _write(tmp_path / "a.md", "some content here")
    settings = Settings(target_dirs=[tmp_path], db_dir=tmp_path / "db")
    store = VectorStore(settings.db_dir, fake_embedder)

    _, first_report = search("content", store, settings)
    _, second_report = search("content", store, settings)

    assert first_report.added == 1
    assert second_report.added == 0
    assert second_report.unchanged == 1


def test_search_sync_false_skips_sync(tmp_path: Path, fake_embedder):
    from notesearch.vectordb import VectorStore

    _write(tmp_path / "a.md", "some content")
    settings = Settings(target_dirs=[tmp_path], db_dir=tmp_path / "db")
    store = VectorStore(settings.db_dir, fake_embedder)

    results, report = search("content", store, settings, sync=False)
    assert report.added == 0  # sync never ran
    assert results == []  # nothing was ever indexed either


def test_search_directory_filter_excludes_other_dirs(tmp_path: Path, fake_embedder):
    from notesearch.vectordb import VectorStore

    _write(tmp_path / "proj_a" / "note.md", "shared keyword content in project a")
    _write(tmp_path / "proj_b" / "note.md", "shared keyword content in project b")
    settings = Settings(target_dirs=[tmp_path], db_dir=tmp_path / "db")
    store = VectorStore(settings.db_dir, fake_embedder)

    results, _ = search("shared keyword", store, settings, top_k=10, directory="proj_a")
    assert results
    assert all("proj_a" in r.metadata["source"] for r in results)


def test_search_top_k_limits_results(tmp_path: Path, fake_embedder):
    from notesearch.vectordb import VectorStore

    for i in range(5):
        _write(tmp_path / f"note{i}.md", f"shared keyword document number {i}")
    settings = Settings(target_dirs=[tmp_path], db_dir=tmp_path / "db")
    store = VectorStore(settings.db_dir, fake_embedder)

    results, _ = search("shared keyword", store, settings, top_k=2)
    assert len(results) <= 2
