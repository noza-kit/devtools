from __future__ import annotations

from typing import Protocol

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Wraps a lazily-loaded SentenceTransformers model (loaded, and its
    weights downloaded from HuggingFace on first use, only on the first
    real `encode()` call -- so importing/constructing this class stays
    cheap, which matters for CLI startup time on commands that don't
    actually need to embed anything)."""

    def __init__(self, model_name: str = MODEL_NAME):
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load()
        return model.encode(texts, convert_to_numpy=True).tolist()
