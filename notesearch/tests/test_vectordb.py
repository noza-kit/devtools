from pathlib import Path

from notesearch.chunking import Chunk
from notesearch.vectordb import VectorStore


def _store(tmp_path: Path, fake_embedder) -> VectorStore:
    return VectorStore(tmp_path / "db", fake_embedder)


def test_upsert_and_count(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    chunks = [Chunk(text="chunk one", heading="H1", start_line=1), Chunk(text="chunk two", heading="H1", start_line=5)]
    store.upsert_document("a.md", chunks, mtime=100.0)
    assert store.count() == 2


def test_get_indexed_sources(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    store.upsert_document("a.md", [Chunk(text="x", heading="")], mtime=100.0)
    store.upsert_document("b.md", [Chunk(text="y", heading="")], mtime=200.0)
    assert store.get_indexed_sources() == {"a.md": 100.0, "b.md": 200.0}


def test_upsert_document_replaces_previous_chunks_entirely(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    store.upsert_document("a.md", [Chunk(text=f"chunk {i}", heading="") for i in range(5)], mtime=100.0)
    assert store.count() == 5

    # document shrank to 2 chunks -- the 3 stale trailing chunks must not survive
    store.upsert_document("a.md", [Chunk(text="only chunk", heading="")], mtime=200.0)
    assert store.count() == 1


def test_delete_document(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    store.upsert_document("a.md", [Chunk(text="x", heading="")], mtime=100.0)
    store.upsert_document("b.md", [Chunk(text="y", heading="")], mtime=100.0)
    store.delete_document("a.md")
    assert store.count() == 1
    assert "a.md" not in store.get_indexed_sources()


def test_delete_document_on_empty_store_does_not_raise(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    store.delete_document("nonexistent.md")  # should not raise


def test_all_chunks_returns_texts_and_metadata(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    store.upsert_document("a.md", [Chunk(text="hello world", heading="Intro", start_line=3)], mtime=100.0)
    ids, texts, metadatas = store.all_chunks()
    assert texts == ["hello world"]
    assert metadatas[0]["heading"] == "Intro"
    assert metadatas[0]["start_line"] == 3
    assert metadatas[0]["source"] == "a.md"
    assert ids[0] == "a.md::0"


def test_query_vector_on_empty_store_returns_empty(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    assert store.query_vector("anything") == {}


def test_query_vector_returns_scores_for_all_chunks(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    store.upsert_document("a.md", [Chunk(text="apple", heading=""), Chunk(text="banana", heading="")], mtime=100.0)
    scores = store.query_vector("apple", n_results=10)
    assert set(scores) == {"a.md::0", "a.md::1"}


def test_query_vector_where_filters_by_directory(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    store.upsert_document(str(Path("proj_a") / "note.md"), [Chunk(text="apple", heading="")], mtime=100.0)
    store.upsert_document(str(Path("proj_b") / "note.md"), [Chunk(text="apple", heading="")], mtime=100.0)

    scores = store.query_vector("apple", n_results=10, where={"directory": "proj_a"})
    ids = list(scores)
    assert len(ids) == 1
    assert ids[0].startswith(str(Path("proj_a")))


def test_directory_metadata_is_parent_folder_name(tmp_path: Path, fake_embedder):
    store = _store(tmp_path, fake_embedder)
    source = str(Path("some") / "project_A" / "note.md")
    store.upsert_document(source, [Chunk(text="x", heading="")], mtime=100.0)
    _, _, metadatas = store.all_chunks()
    assert metadatas[0]["directory"] == "project_A"
