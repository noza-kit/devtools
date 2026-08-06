from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """A deliberately simple tokenizer (lowercased \\w+ runs) -- good
    enough for BM25's exact-term matching (variable names, IDs,
    technical terms) without pulling in a real Japanese morphological
    analyzer, which is a heavier dependency than this project's
    "軽量・多言語対応" (SentenceTransformers already covers meaning-level
    Japanese matching; BM25's job here is exact-term matching, where
    even a crude tokenizer is useful)."""
    return _TOKEN_RE.findall(text.lower())


@dataclass(frozen=True)
class BM25Result:
    chunk_id: str
    score: float


class BM25Index:
    """An in-memory BM25 index built fresh from whatever chunk texts are
    currently in the vector DB (see sync.py) -- rank_bm25 doesn't
    persist to disk on its own, and rebuilding from ChromaDB's already-
    persisted documents on each search is simpler than maintaining a
    second on-disk index that could drift out of sync with the first."""

    def __init__(self, chunk_ids: list[str], texts: list[str]):
        if len(chunk_ids) != len(texts):
            raise ValueError("chunk_ids and texts must be the same length")
        self._chunk_ids = chunk_ids
        self._bm25 = BM25Okapi([tokenize(t) for t in texts]) if texts else None

    def search(self, query: str, top_k: int = 10) -> list[BM25Result]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(zip(self._chunk_ids, scores), key=lambda pair: pair[1], reverse=True)
        return [BM25Result(chunk_id=cid, score=float(score)) for cid, score in ranked[:top_k] if score > 0]
