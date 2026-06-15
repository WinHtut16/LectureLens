"""Unit tests for VectorStore — pure FAISS logic, deterministic, no mocks."""

import os
import tempfile

import numpy as np
import pytest

from app.ml.vector_store import SearchResult, VectorStore, MockVectorStore, VectorStoreProtocol


def _unit_vec(dim: int = 384, hot: int = 0) -> np.ndarray:
    """L2-unit vector with 1.0 at index `hot`."""
    v = np.zeros(dim, dtype=np.float32)
    v[hot] = 1.0
    return v


# ---------------------------------------------------------------------------
# Empty store
# ---------------------------------------------------------------------------


def test_search_empty_store_returns_empty():
    vs = VectorStore()
    assert vs.search(_unit_vec(hot=0), recording_ids=["rec-1"]) == []


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_search_returns_results_ranked_by_similarity():
    vs = VectorStore()
    for i in range(5):
        vs.add(
            segment_id=f"seg-{i}",
            recording_id="rec-1",
            start_seconds=float(i * 10),
            speaker_label=None,
            vector=_unit_vec(hot=i),
        )
    results = vs.search(_unit_vec(hot=2), recording_ids=["rec-1"], k=5)
    assert len(results) == 5
    assert results[0].segment_id == "seg-2"
    assert results[0].score == pytest.approx(1.0, abs=1e-5)
    for r in results[1:]:
        assert r.score == pytest.approx(0.0, abs=1e-5)


# ---------------------------------------------------------------------------
# recording_id filter
# ---------------------------------------------------------------------------


def test_recording_id_filter_excludes_other_recordings():
    vs = VectorStore()
    vs.add("seg-A", "rec-A", 0.0, None, _unit_vec(hot=0))
    vs.add("seg-B", "rec-B", 0.0, None, _unit_vec(hot=0))

    results = vs.search(_unit_vec(hot=0), recording_ids=["rec-A"], k=10)
    assert len(results) == 1
    assert results[0].segment_id == "seg-A"


def test_multiple_recording_ids_searched():
    vs = VectorStore()
    vs.add("seg-A", "rec-A", 0.0, None, _unit_vec(hot=1))
    vs.add("seg-B", "rec-B", 0.0, None, _unit_vec(hot=1))
    vs.add("seg-C", "rec-C", 0.0, None, _unit_vec(hot=1))

    results = vs.search(_unit_vec(hot=1), recording_ids=["rec-A", "rec-B"], k=10)
    seg_ids = {r.segment_id for r in results}
    assert seg_ids == {"seg-A", "seg-B"}


# ---------------------------------------------------------------------------
# speaker_label filter
# ---------------------------------------------------------------------------


def test_speaker_label_filter_returns_only_matching():
    vs = VectorStore()
    vs.add("seg-S1", "rec-1", 0.0, "Speaker 1", _unit_vec(hot=0))
    vs.add("seg-S2", "rec-1", 10.0, "Speaker 2", _unit_vec(hot=0))

    results = vs.search(
        _unit_vec(hot=0),
        recording_ids=["rec-1"],
        k=10,
        speaker_label="Speaker 1",
    )
    assert len(results) == 1
    assert results[0].segment_id == "seg-S1"
    assert results[0].speaker_label == "Speaker 1"


def test_speaker_label_none_returns_all():
    vs = VectorStore()
    vs.add("seg-1", "rec-1", 0.0, "Speaker 1", _unit_vec(hot=0))
    vs.add("seg-2", "rec-1", 10.0, "Speaker 2", _unit_vec(hot=0))

    results = vs.search(_unit_vec(hot=0), recording_ids=["rec-1"], k=10)
    assert len(results) == 2


# ---------------------------------------------------------------------------
# k limit
# ---------------------------------------------------------------------------


def test_k_limits_result_count():
    vs = VectorStore()
    for i in range(10):
        vs.add(f"seg-{i}", "rec-1", float(i), None, _unit_vec(hot=i))
    results = vs.search(_unit_vec(hot=0), recording_ids=["rec-1"], k=3)
    assert len(results) <= 3


# ---------------------------------------------------------------------------
# save / load round-trip
# ---------------------------------------------------------------------------


def test_save_load_round_trip():
    vs = VectorStore()
    vs.add("seg-0", "rec-x", 5.0, "Spk", _unit_vec(hot=3))

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "faiss.index")
        vs.save(path)

        vs2 = VectorStore()
        vs2.load(path)
        results = vs2.search(_unit_vec(hot=3), recording_ids=["rec-x"], k=1)

    assert len(results) == 1
    r = results[0]
    assert r.segment_id == "seg-0"
    assert r.start_seconds == pytest.approx(5.0)
    assert r.speaker_label == "Spk"
    assert r.score == pytest.approx(1.0, abs=1e-5)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_mock_vector_store_satisfies_protocol():
    assert isinstance(MockVectorStore(), VectorStoreProtocol)
