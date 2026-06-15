"""Sentence-transformer embedding interface and implementations.

SentenceTransformer is imported lazily inside Embedder.__init__ so this
module is safe to import in unit tests without triggering a model download.
"""

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class EmbedderProtocol(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray: ...
    def embed_one(self, text: str) -> np.ndarray: ...


class Embedder:
    """all-MiniLM-L6-v2 wrapper. Vectors are L2-normalised on output."""

    DIM: int = 384

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return float32 L2-normalised embeddings, shape (len(texts), 384)."""
        vecs: np.ndarray = self._model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vecs.astype(np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        """Return shape (384,)."""
        return self.embed([text])[0]


class MockEmbedder:
    """Deterministic L2-unit-vector embeddings for tests — no model loaded."""

    DIM: int = 384

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return shape (len(texts), 384), dtype float32, each row L2-normalised."""
        n = len(texts)
        vecs = np.zeros((n, self.DIM), dtype=np.float32)
        for i in range(n):
            vecs[i, i % self.DIM] = 1.0  # distinct unit vector per slot
        return vecs

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]
