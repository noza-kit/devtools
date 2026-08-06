from __future__ import annotations

import hashlib

import pytest


class FakeEmbedder:
    """Deterministic, dependency-free stand-in for SentenceTransformerEmbedder:
    hashes each text into a small fixed-size vector. Doesn't capture real
    semantic similarity (unlike the real model), so tests that need
    "finds the semantically-related document" rely on BM25's exact-term
    matching instead -- see hybrid search tests, which use queries that
    share literal keywords with the expected top result."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[b / 255.0 for b in hashlib.sha256(t.encode("utf-8")).digest()[:16]] for t in texts]


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()
