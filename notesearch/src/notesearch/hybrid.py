from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

DEFAULT_VECTOR_WEIGHT = 0.5
DEFAULT_BM25_WEIGHT = 0.5


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    text: str
    metadata: dict = field(default_factory=dict)
    vector_score: float = 0.0  # min-max normalized within this query's results, 0-1
    bm25_score: float = 0.0  # min-max normalized within this query's results, 0-1
    combined_score: float = 0.0


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Min-max normalize to [0, 1]. All-equal input (including the
    single-item and empty cases) maps to 1.0 for every key rather than
    dividing by zero -- "no discriminating signal" is treated as "don't
    let this method's score suppress the other method's ranking."""
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi == lo:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def combine_results(
    vector_scores: dict[str, float],
    bm25_scores: dict[str, float],
    content_lookup: dict[str, dict],
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
) -> list[SearchResult]:
    """Fuse two independent rankings (vector similarity, BM25 keyword
    score) over the same chunk-id space into one combined ranking, each
    normalized to [0, 1] before weighting so the two methods'
    differently-scaled raw scores don't dominate each other by
    magnitude alone. `content_lookup` (chunk_id -> {"text":...,
    "metadata":...}) supplies the actual chunk content for hits found
    by only one of the two methods -- BM25 itself doesn't carry
    metadata, and a chunk outside the vector search's top-k still needs
    its text if BM25 surfaced it."""
    norm_vector = normalize_scores(vector_scores)
    norm_bm25 = normalize_scores(bm25_scores)

    results = []
    for chunk_id in set(norm_vector) | set(norm_bm25):
        v = norm_vector.get(chunk_id, 0.0)
        b = norm_bm25.get(chunk_id, 0.0)
        info = content_lookup.get(chunk_id, {})
        results.append(
            SearchResult(
                chunk_id=chunk_id,
                text=info.get("text", ""),
                metadata=info.get("metadata", {}),
                vector_score=v,
                bm25_score=b,
                combined_score=vector_weight * v + bm25_weight * b,
            )
        )

    results.sort(key=lambda r: r.combined_score, reverse=True)
    return results
