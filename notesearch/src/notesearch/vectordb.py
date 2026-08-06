from __future__ import annotations

from pathlib import Path
from typing import Optional

from notesearch.chunking import Chunk
from notesearch.embeddings import Embedder


class VectorStore:
    """ChromaDB-backed chunk store (persisted at `persist_dir`). This is
    the source of truth for both vector search and, via all_chunks(),
    the corpus BM25Index is rebuilt from and the content_lookup hybrid
    search needs for chunks a query surfaces (see search.py)."""

    def __init__(self, persist_dir: Path, embedder: Embedder, collection_name: str = "notesearch"):
        import chromadb

        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(collection_name)
        self._embedder = embedder

    def get_indexed_sources(self) -> dict[str, float]:
        """{source path: last_modified}, one entry per distinct source
        currently indexed (chunks share their source's last_modified,
        so the max across a source's chunks is that source's value)."""
        data = self._collection.get(include=["metadatas"])
        result: dict[str, float] = {}
        for meta in data["metadatas"] or []:
            source, mtime = meta.get("source"), meta.get("last_modified")
            if source is not None and mtime is not None:
                result[source] = max(result.get(source, 0.0), mtime)
        return result

    def upsert_document(self, source: str, chunks: list[Chunk], mtime: float) -> None:
        """Replaces (delete then re-add, not a partial update) every
        chunk previously indexed for `source` -- necessary because a
        changed document can have a different chunk count than before,
        and a same-index upsert would leave stale trailing chunks from
        a document that shrank."""
        self.delete_document(source)
        if not chunks:
            return

        ids = [f"{source}::{i}" for i in range(len(chunks))]
        texts = [c.text for c in chunks]
        embeddings = self._embedder.encode(texts)
        directory = Path(source).parent.name
        metadatas = [
            {
                "source": source,
                "directory": directory,
                "heading": c.heading,
                "last_modified": mtime,
                "start_line": c.start_line,
            }
            for c in chunks
        ]
        self._collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    def delete_document(self, source: str) -> None:
        if self._collection.count() > 0:
            self._collection.delete(where={"source": source})

    def all_chunks(self) -> tuple[list[str], list[str], list[dict]]:
        """(chunk_ids, texts, metadatas) for every chunk currently
        indexed -- the full corpus BM25Index is built from."""
        data = self._collection.get(include=["documents", "metadatas"])
        return data["ids"], data["documents"] or [], data["metadatas"] or []

    def query_vector(self, query_text: str, n_results: int = 10, where: Optional[dict] = None) -> dict[str, float]:
        """{chunk_id: score}, higher = more similar. ChromaDB's default
        distance metric is smaller-is-more-similar, so scores here are
        the negated distance -- min-max normalization in hybrid.py
        doesn't care about the absolute scale, only that "higher is
        better" holds, which negation guarantees."""
        count = self._collection.count()
        if count == 0:
            return {}
        embedding = self._embedder.encode([query_text])[0]
        result = self._collection.query(
            query_embeddings=[embedding], n_results=min(n_results, count), where=where
        )
        return {cid: -dist for cid, dist in zip(result["ids"][0], result["distances"][0])}

    def count(self) -> int:
        return self._collection.count()
