"""Unit tests for the embedding stage in process_recording.

All ML components mocked — asserts that embedder is called with correct texts,
vector_store.add called once per segment, save called, and status transitions
go through 'embedding' before 'ready'.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import Recording, RecordingStatus
from app.ml.embedder import MockEmbedder
from app.ml.transcriber import MockTranscriber, TranscriptSegment
from app.ml.vector_store import MockVectorStore
from app.worker.pipeline import process_recording


# ---------------------------------------------------------------------------
# Helpers  (same pattern as test_worker_pipeline.py)
# ---------------------------------------------------------------------------


def _make_recording(status: RecordingStatus = RecordingStatus.queued) -> MagicMock:
    rec = MagicMock(spec=Recording)
    rec.id = uuid.uuid4()
    rec.status = status
    rec.audio_path = f"audio/user/{rec.id}.mp3"
    rec.duration_seconds = None
    return rec


def _make_session_factory(recording: MagicMock | None) -> MagicMock:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=recording)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock()
    factory.return_value = session
    return factory


def _make_storage(audio_bytes: bytes = b"fake-audio") -> MagicMock:
    storage = AsyncMock()
    storage.download_file = AsyncMock(return_value=audio_bytes)
    return storage


_THREE_SEGMENTS = [
    TranscriptSegment(start=0.0, end=10.0, text="first"),
    TranscriptSegment(start=10.0, end=20.0, text="second"),
    TranscriptSegment(start=20.0, end=30.0, text="third"),
]


def _base_ctx(
    factory: MagicMock,
    storage: MagicMock,
    transcriber: MockTranscriber,
    embedder: MagicMock | MockEmbedder | None = None,
    vector_store: MockVectorStore | None = None,
) -> dict:
    return {
        "db_session_factory": factory,
        "storage": storage,
        "transcriber": transcriber,
        "embedder": embedder if embedder is not None else MockEmbedder(),
        "vector_store": vector_store if vector_store is not None else MockVectorStore(),
    }


# ---------------------------------------------------------------------------
# Embedding stage behaviour
# ---------------------------------------------------------------------------


async def test_embedder_called_with_segment_texts():
    """After chunking 3 × 10s segments, embedder.embed called with the chunk text(s)."""
    rec = _make_recording()
    factory = _make_session_factory(rec)
    storage = _make_storage()
    spy_embedder = MagicMock(wraps=MockEmbedder())
    mock_vs = MockVectorStore()

    ctx = _base_ctx(factory, storage, MockTranscriber(_THREE_SEGMENTS), spy_embedder, mock_vs)

    with (
        patch("app.worker.pipeline.tempfile.NamedTemporaryFile") as mock_tmp,
        patch("app.worker.pipeline.os.unlink"),
    ):
        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/f.mp3"))
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/f.mp3"
        await process_recording(ctx, str(rec.id))

    spy_embedder.embed.assert_called_once()
    texts_arg: list[str] = spy_embedder.embed.call_args[0][0]
    assert len(texts_arg) >= 1
    assert all(isinstance(t, str) and t for t in texts_arg)


async def test_vector_store_add_called_once_per_chunk():
    """One add() call per chunk produced from the segments."""
    rec = _make_recording()
    factory = _make_session_factory(rec)
    storage = _make_storage()
    mock_vs = MockVectorStore()

    ctx = _base_ctx(factory, storage, MockTranscriber(_THREE_SEGMENTS), vector_store=mock_vs)

    with (
        patch("app.worker.pipeline.tempfile.NamedTemporaryFile") as mock_tmp,
        patch("app.worker.pipeline.os.unlink"),
    ):
        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/f.mp3"))
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/f.mp3"
        await process_recording(ctx, str(rec.id))

    # 3 × 10s segments fit in one 30s chunk → 1 add() call
    assert len(mock_vs._entries) == 1
    entry_meta = mock_vs._entries[0][0]
    assert entry_meta["recording_id"] == str(rec.id)
    assert entry_meta["start_seconds"] == pytest.approx(0.0)


async def test_vector_store_save_called_once():
    rec = _make_recording()
    factory = _make_session_factory(rec)
    storage = _make_storage()
    mock_vs = MockVectorStore()

    ctx = _base_ctx(factory, storage, MockTranscriber(_THREE_SEGMENTS), vector_store=mock_vs)

    with (
        patch("app.worker.pipeline.tempfile.NamedTemporaryFile") as mock_tmp,
        patch("app.worker.pipeline.os.unlink"),
    ):
        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/f.mp3"))
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/f.mp3"
        await process_recording(ctx, str(rec.id))

    assert mock_vs.save_call_count == 1


async def test_status_transitions_include_embedding():
    """Status sequence must include 'embedding' between 'transcribing' and 'ready'."""
    rec = _make_recording()
    statuses: list[RecordingStatus] = []

    async def _capture():
        statuses.append(rec.status)

    factory = _make_session_factory(rec)
    factory.return_value.commit = _capture
    storage = _make_storage()

    ctx = _base_ctx(factory, storage, MockTranscriber(_THREE_SEGMENTS))

    with (
        patch("app.worker.pipeline.tempfile.NamedTemporaryFile") as mock_tmp,
        patch("app.worker.pipeline.os.unlink"),
    ):
        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/f.mp3"))
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/f.mp3"
        await process_recording(ctx, str(rec.id))

    assert RecordingStatus.transcribing in statuses
    assert RecordingStatus.embedding in statuses
    assert statuses[-1] == RecordingStatus.ready
    t_idx = statuses.index(RecordingStatus.transcribing)
    e_idx = statuses.index(RecordingStatus.embedding)
    r_idx = len(statuses) - 1
    assert t_idx < e_idx < r_idx


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------


async def test_embedder_raises_sets_failed_status():
    """If embedder.embed raises, status=failed with error_message."""
    rec = _make_recording()
    err_rec = _make_recording()
    err_rec.id = rec.id

    main_session = AsyncMock()
    main_session.scalar = AsyncMock(return_value=rec)
    main_session.commit = AsyncMock()
    main_session.rollback = AsyncMock()
    main_session.add = MagicMock()
    main_session.__aenter__ = AsyncMock(return_value=main_session)
    main_session.__aexit__ = AsyncMock(return_value=False)

    err_session = AsyncMock()
    err_session.scalar = AsyncMock(return_value=err_rec)
    err_session.commit = AsyncMock()
    err_session.__aenter__ = AsyncMock(return_value=err_session)
    err_session.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(side_effect=[main_session, err_session])

    boom_embedder = MagicMock(spec=MockEmbedder)
    boom_embedder.embed = MagicMock(side_effect=RuntimeError("embed exploded"))

    ctx = {
        "db_session_factory": factory,
        "storage": _make_storage(),
        "transcriber": MockTranscriber(_THREE_SEGMENTS),
        "embedder": boom_embedder,
        "vector_store": MockVectorStore(),
    }

    with (
        patch("app.worker.pipeline.tempfile.NamedTemporaryFile") as mock_tmp,
        patch("app.worker.pipeline.os.unlink"),
        pytest.raises(RuntimeError, match="embed exploded"),
    ):
        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/f.mp3"))
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/f.mp3"
        await process_recording(ctx, str(rec.id))

    assert err_rec.status == RecordingStatus.failed
    assert "embed exploded" in err_rec.error_message
