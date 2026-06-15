"""FAISS-backed in-memory vector store with per-vector metadata for filtered search.

Vectors must be L2-normalised before insertion (Embedder guarantees this),
so IndexFlatIP inner-product scores equal cosine similarity.
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import faiss  # type: ignore[import-untyped]
import numpy as np


@dataclass(frozen=True)
class SearchResult:
    segment_id: str
    recording_id: str
    start_seconds: float
    score: float
    speaker_label: str | None


@runtime_checkable
class VectorStoreProtocol(Protocol):
    def add(
        self,
        segment_id: str,
        recording_id: str,
        start_seconds: float,
        speaker_label: str | None,
        vector: np.ndarray,
    ) -> None: ...

    def search(
        self,
        query_vector: np.ndarray,
        recording_ids: list[str],
        k: int,
        speaker_label: str | None,
    ) -> list[SearchResult]: ...

    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...


class VectorStore:
    """In-memory FAISS IndexFlatIP with parallel metadata list."""

    def __init__(self, dim: int = 384) -> None:
        self._dim = dim
        self._index: faiss.Index = faiss.IndexFlatIP(dim)
        self._meta: list[dict[str, Any]] = []

    def add(
        self,
        segment_id: str,
        recording_id: str,
        start_seconds: float,
        speaker_label: str | None,
        vector: np.ndarray,
    ) -> None:
        self._index.add(np.array(vector, dtype=np.float32).reshape(1, -1))
        self._meta.append(
            {
                "segment_id": segment_id,
                "recording_id": recording_id,
                "start_seconds": start_seconds,
                "speaker_label": speaker_label,
            }
        )

    def search(
        self,
        query_vector: np.ndarray,
        recording_ids: list[str],
        k: int = 10,
        speaker_label: str | None = None,
    ) -> list[SearchResult]:
        if self._index.ntotal == 0:
            return []
        rid_set = set(recording_ids)
        # Fetch enough candidates to survive post-filtering
        search_k = min(self._index.ntotal, max(k * 10, 100))
        scores, indices = self._index.search(
            np.array(query_vector, dtype=np.float32).reshape(1, -1), search_k
        )
        results: list[SearchResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                break
            meta = self._meta[int(idx)]
            if meta["recording_id"] not in rid_set:
                continue
            if speaker_label is not None and meta["speaker_label"] != speaker_label:
                continue
            results.append(
                SearchResult(
                    segment_id=meta["segment_id"],
                    recording_id=meta["recording_id"],
                    start_seconds=meta["start_seconds"],
                    score=float(score),
                    speaker_label=meta["speaker_label"],
                )
            )
            if len(results) == k:
                break
        return results

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        faiss.write_index(self._index, path)
        with open(path + ".meta.json", "w") as f:
            json.dump(self._meta, f)

    def load(self, path: str) -> None:
        self._index = faiss.read_index(path)
        with open(path + ".meta.json") as f:
            self._meta = json.load(f)


class MockVectorStore(VectorStoreProtocol):
    """Pure-Python mock — no FAISS dependency, suitable for unit tests."""

    def __init__(self) -> None:
        self._entries: list[tuple[dict[str, Any], np.ndarray]] = []
        self.save_call_count: int = 0

    def add(
        self,
        segment_id: str,
        recording_id: str,
        start_seconds: float,
        speaker_label: str | None,
        vector: np.ndarray,
    ) -> None:
        self._entries.append(
            (
                {
                    "segment_id": segment_id,
                    "recording_id": recording_id,
                    "start_seconds": start_seconds,
                    "speaker_label": speaker_label,
                },
                np.array(vector, dtype=np.float32).copy(),
            )
        )

    def search(
        self,
        query_vector: np.ndarray,
        recording_ids: list[str],
        k: int = 10,
        speaker_label: str | None = None,
    ) -> list[SearchResult]:
        rid_set = set(recording_ids)
        scored: list[tuple[float, dict[str, Any]]] = []
        for meta, vec in self._entries:
            if meta["recording_id"] not in rid_set:
                continue
            if speaker_label is not None and meta["speaker_label"] != speaker_label:
                continue
            scored.append((float(np.dot(query_vector, vec)), meta))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [
            SearchResult(
                segment_id=m["segment_id"],
                recording_id=m["recording_id"],
                start_seconds=m["start_seconds"],
                score=s,
                speaker_label=m["speaker_label"],
            )
            for s, m in scored[:k]
        ]

    def save(self, path: str) -> None:
        self.save_call_count += 1

    def load(self, path: str) -> None:
        pass
