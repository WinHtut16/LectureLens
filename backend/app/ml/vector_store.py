"""FAISS-backed vector store with one index per recording for correct pre-filtering.

Each recording has its own IndexFlatIP so searches are scoped to the recording
before ranking — not post-filtered from a global index.  Vectors must be
L2-normalised before insertion (Embedder guarantees this), so IndexFlatIP
inner-product scores equal cosine similarity.

When constructed with index_dir, search() loads per-recording index files from
disk on first access so worker writes are always visible to the API without a
restart.
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
    """Per-recording FAISS IndexFlatIP — searches are scoped to the target recording."""

    def __init__(self, dim: int = 384, index_dir: str | None = None) -> None:
        self._dim = dim
        # If set, search() loads missing recording indexes from this directory on demand.
        self._index_dir = index_dir
        self._per_recording: dict[str, tuple[faiss.Index, list[dict[str, Any]]]] = {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(
        self,
        segment_id: str,
        recording_id: str,
        start_seconds: float,
        speaker_label: str | None,
        vector: np.ndarray,
    ) -> None:
        if recording_id not in self._per_recording:
            self._per_recording[recording_id] = (faiss.IndexFlatIP(self._dim), [])
        index, meta = self._per_recording[recording_id]
        index.add(np.array(vector, dtype=np.float32).reshape(1, -1))
        meta.append(
            {
                "segment_id": segment_id,
                "recording_id": recording_id,
                "start_seconds": start_seconds,
                "speaker_label": speaker_label,
            }
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def _get_recording_data(
        self, recording_id: str
    ) -> tuple[faiss.Index | None, list[dict[str, Any]]]:
        """Return (index, meta) from memory, loading from disk on cache miss."""
        if recording_id in self._per_recording:
            return self._per_recording[recording_id]
        if self._index_dir is not None:
            index_path = os.path.join(self._index_dir, f"{recording_id}.index")
            meta_path = index_path + ".meta.json"
            if os.path.exists(index_path) and os.path.exists(meta_path):
                index = faiss.read_index(index_path)
                with open(meta_path) as f:
                    loaded_meta: list[dict[str, Any]] = json.load(f)
                # Cache for this instance's lifetime (integration tests reuse the object).
                self._per_recording[recording_id] = (index, loaded_meta)
                return self._per_recording[recording_id]
        return None, []

    def search(
        self,
        query_vector: np.ndarray,
        recording_ids: list[str],
        k: int = 10,
        speaker_label: str | None = None,
    ) -> list[SearchResult]:
        qvec = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        all_results: list[SearchResult] = []

        for rid in recording_ids:
            index, meta = self._get_recording_data(rid)
            if index is None or index.ntotal == 0:
                continue
            # Overfetch only when a speaker filter will cull some results.
            fetch_k = min(index.ntotal, k if speaker_label is None else k * 10)
            scores, indices = index.search(qvec, fetch_k)
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    break
                m = meta[int(idx)]
                if speaker_label is not None and m["speaker_label"] != speaker_label:
                    continue
                all_results.append(
                    SearchResult(
                        segment_id=m["segment_id"],
                        recording_id=m["recording_id"],
                        start_seconds=m["start_seconds"],
                        score=float(score),
                        speaker_label=m["speaker_label"],
                    )
                )

        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:k]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Write each recording's index to {path}/{recording_id}.index[.meta.json]."""
        os.makedirs(path, exist_ok=True)
        for rid, (index, meta) in self._per_recording.items():
            faiss.write_index(index, os.path.join(path, f"{rid}.index"))
            with open(os.path.join(path, f"{rid}.index.meta.json"), "w") as f:
                json.dump(meta, f)

    def load(self, path: str) -> None:
        """Eagerly load all recording indexes from a directory (e.g. for pre-warming)."""
        if not os.path.isdir(path):
            return
        for fname in os.listdir(path):
            if not fname.endswith(".index"):
                continue
            rid = fname[: -len(".index")]
            meta_path = os.path.join(path, fname + ".meta.json")
            if not os.path.exists(meta_path):
                continue
            index = faiss.read_index(os.path.join(path, fname))
            with open(meta_path) as f:
                meta: list[dict[str, Any]] = json.load(f)
            self._per_recording[rid] = (index, meta)


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
