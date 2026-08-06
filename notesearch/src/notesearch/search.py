from __future__ import annotations

import time
from typing import Optional

from notesearch.bm25index import BM25Index
from notesearch.config import Settings
from notesearch.hybrid import SearchResult, combine_results
from notesearch.sync import SyncReport, sync_index
from notesearch.vectordb import VectorStore


def build_where_clause(directory: Optional[str] = None, since_days: Optional[int] = None, now: Optional[float] = None) -> Optional[dict]:
    """ChromaDB `where` clause for the --dir/--days metadata filters."""
    clauses = []
    if directory:
        clauses.append({"directory": directory})
    if since_days is not None:
        cutoff = (now if now is not None else time.time()) - since_days * 86400
        clauses.append({"last_modified": {"$gte": cutoff}})

    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _matches_filter(metadata: dict, directory: Optional[str], since_days: Optional[int], now: Optional[float] = None) -> bool:
    """The same --dir/--days logic as build_where_clause, applied
    client-side to the full chunk corpus before building the BM25
    index -- rank_bm25 has no metadata-filtering concept of its own, so
    without this, BM25 results could surface chunks outside the scope
    the vector side (via ChromaDB's `where`) is already restricted to."""
    if directory and metadata.get("directory") != directory:
        return False
    if since_days is not None:
        cutoff = (now if now is not None else time.time()) - since_days * 86400
        if metadata.get("last_modified", 0) < cutoff:
            return False
    return True


def search(
    query: str,
    store: VectorStore,
    settings: Settings,
    top_k: int = 10,
    directory: Optional[str] = None,
    since_days: Optional[int] = None,
    sync: bool = True,
) -> tuple[list[SearchResult], SyncReport]:
    """The full hybrid-search pipeline: JIT-sync the index (unless
    `sync=False`, e.g. a caller that just synced), vector-search via
    ChromaDB, keyword-search via a freshly-built BM25 index over the
    (optionally --dir/--days-filtered) full corpus, then fuse the two
    rankings. Returns the top `top_k` combined results plus the sync
    report (added/updated/unchanged file counts) so the CLI can report
    what JIT sync did."""
    report = sync_index(store, settings) if sync else SyncReport()

    where = build_where_clause(directory, since_days)
    vector_scores = store.query_vector(query, n_results=top_k * 2, where=where)

    chunk_ids, texts, metadatas = store.all_chunks()
    if directory or since_days is not None:
        filtered = [
            (cid, t, m) for cid, t, m in zip(chunk_ids, texts, metadatas) if _matches_filter(m, directory, since_days)
        ]
        chunk_ids = [c for c, _, _ in filtered]
        texts = [t for _, t, _ in filtered]
        metadatas = [m for _, _, m in filtered]

    bm25_results = BM25Index(chunk_ids, texts).search(query, top_k=top_k * 2)
    bm25_scores = {r.chunk_id: r.score for r in bm25_results}

    content_lookup = {cid: {"text": t, "metadata": m} for cid, t, m in zip(chunk_ids, texts, metadatas)}
    results = combine_results(vector_scores, bm25_scores, content_lookup)

    return results[:top_k], report
