"""Unit tests for app.services.search_service — DB, embedder, and vector_store mocked."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import Recording, RecordingStatus, Segment, SourceType
from app.ml.embedder import MockEmbedder
from app.ml.vector_store import MockVectorStore
from app.services.search_service import search_recording

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_recording(
    user_id: uuid.UUID,
    status: RecordingStatus = RecordingStatus.ready,
) -> Recording:
    r = Recording()
    r.id = uuid.uuid4()
    r.user_id = user_id
    r.title = "test.mp3"
    r.source_type = SourceType.upload
    r.source_url = None
    r.audio_path = f"audio/{user_id}/{r.id}.mp3"
    r.duration_seconds = 60
    r.status = status
    r.error_message = None
    r.created_at = datetime.now(UTC)
    return r


def _make_segment(recording_id: uuid.UUID, idx: int = 0) -> Segment:
    s = Segment()
    s.id = uuid.uuid4()
    s.recording_id = recording_id
    s.start_seconds = float(idx * 30)
    s.end_seconds = float(idx * 30 + 30)
    s.text = f"segment text {idx}"
    s.speaker_label = None
    s.segment_index = idx
    s.created_at = datetime.now(UTC)
    return s


def _mock_db(recording: Recording | None, segments: list[Segment] | None = None) -> AsyncMock:
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=recording)
    scalars_mock = MagicMock()
    scalars_mock.__iter__ = MagicMock(return_value=iter(segments or []))
    db.scalars = AsyncMock(return_value=scalars_mock)
    return db


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_search_returns_hits_with_correct_fields():
    user_id = uuid.uuid4()
    rec = _make_recording(user_id)
    seg = _make_segment(rec.id, idx=0)

    # Seed MockVectorStore with the segment vector
    emb = MockEmbedder()
    vs = MockVectorStore()
    vec = emb.embed_one(seg.text)
    vs.add(
        segment_id=str(seg.id),
        recording_id=str(rec.id),
        start_seconds=seg.start_seconds,
        speaker_label=seg.speaker_label,
        vector=vec,
    )

    db = _mock_db(rec, [seg])

    hits, query_ms = await search_recording(
        db,
        emb,
        vs,
        user_id=user_id,
        recording_id=rec.id,
        query="some query",
        k=5,
    )

    assert len(hits) == 1
    h = hits[0]
    assert h.segment_id == str(seg.id)
    assert h.start_seconds == pytest.approx(seg.start_seconds)
    assert h.end_seconds == pytest.approx(seg.end_seconds)
    assert h.text == seg.text
    assert isinstance(h.score, float)
    assert query_ms >= 0.0


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


async def test_returns_403_when_recording_belongs_to_other_user():
    owner_id = uuid.uuid4()
    caller_id = uuid.uuid4()
    rec = _make_recording(owner_id)  # belongs to owner_id, not caller_id

    db = _mock_db(rec)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await search_recording(
            db,
            MockEmbedder(),
            MockVectorStore(),
            user_id=caller_id,
            recording_id=rec.id,
            query="hello",
        )
    assert exc_info.value.status_code == 403


async def test_returns_404_when_recording_not_found():
    db = _mock_db(recording=None)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await search_recording(
            db,
            MockEmbedder(),
            MockVectorStore(),
            user_id=uuid.uuid4(),
            recording_id=uuid.uuid4(),
            query="hello",
        )
    assert exc_info.value.status_code == 404


async def test_returns_400_when_recording_not_ready():
    user_id = uuid.uuid4()
    rec = _make_recording(user_id, status=RecordingStatus.embedding)

    db = _mock_db(rec)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await search_recording(
            db,
            MockEmbedder(),
            MockVectorStore(),
            user_id=user_id,
            recording_id=rec.id,
            query="hello",
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "not_indexed"


# ---------------------------------------------------------------------------
# k cap is respected by the VectorStore layer (tested here end-to-end)
# ---------------------------------------------------------------------------


async def test_k_cap_limits_results():
    user_id = uuid.uuid4()
    rec = _make_recording(user_id)
    emb = MockEmbedder()
    vs = MockVectorStore()

    segments: list[Segment] = []
    for i in range(5):
        seg = _make_segment(rec.id, idx=i)
        segments.append(seg)
        vs.add(str(seg.id), str(rec.id), seg.start_seconds, None, emb.embed_one(seg.text))

    db = _mock_db(rec, segments)

    hits, _ = await search_recording(
        db, emb, vs, user_id=user_id, recording_id=rec.id, query="q", k=2
    )
    assert len(hits) <= 2


# ---------------------------------------------------------------------------
# Empty results (no vectors indexed)
# ---------------------------------------------------------------------------


async def test_empty_vector_store_returns_empty_hits():
    user_id = uuid.uuid4()
    rec = _make_recording(user_id)
    db = _mock_db(rec, [])

    hits, ms = await search_recording(
        db,
        MockEmbedder(),
        MockVectorStore(),
        user_id=user_id,
        recording_id=rec.id,
        query="anything",
    )
    assert hits == []
    assert ms >= 0.0
