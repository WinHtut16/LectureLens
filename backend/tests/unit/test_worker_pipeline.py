"""Unit tests for app.worker.pipeline — DB, storage, and transcriber are all mocked."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import Recording, RecordingStatus
from app.ml.embedder import MockEmbedder
from app.ml.transcriber import MockTranscriber, TranscriptSegment
from app.ml.vector_store import MockVectorStore
from app.worker.pipeline import process_recording

# ---------------------------------------------------------------------------
# Helpers
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


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_happy_path_inserts_segments_and_sets_ready():
    """Mock transcriber returning 3 segments → Segment rows added, status=ready, duration set."""
    rec = _make_recording()
    factory = _make_session_factory(rec)
    storage = _make_storage()
    transcriber = MockTranscriber(segments=_THREE_SEGMENTS)

    ctx = {
        "db_session_factory": factory,
        "storage": storage,
        "transcriber": transcriber,
        "embedder": MockEmbedder(),
        "vector_store": MockVectorStore(),
    }

    with (
        patch("app.worker.pipeline.tempfile.NamedTemporaryFile") as mock_tmp,
        patch("app.worker.pipeline.os.unlink"),
    ):
        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/fake.mp3"))
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/fake.mp3"
        await process_recording(ctx, str(rec.id))

    session = factory.return_value
    # session.add called at least once (for the chunk(s))
    assert session.add.call_count >= 1
    # Final status is ready
    assert rec.status == RecordingStatus.ready
    # duration_seconds set from last segment end (30.0 → int → 30)
    assert rec.duration_seconds == 30


async def test_happy_path_status_transitions_in_order():
    """Status must go: transcribing commit → (work) → ready commit."""
    rec = _make_recording()
    statuses_at_commit: list[RecordingStatus] = []

    async def capture_commit() -> None:
        statuses_at_commit.append(rec.status)

    factory = _make_session_factory(rec)
    factory.return_value.commit = capture_commit

    storage = _make_storage()
    transcriber = MockTranscriber(segments=_THREE_SEGMENTS)

    ctx = {
        "db_session_factory": factory,
        "storage": storage,
        "transcriber": transcriber,
        "embedder": MockEmbedder(),
        "vector_store": MockVectorStore(),
    }

    with (
        patch("app.worker.pipeline.tempfile.NamedTemporaryFile") as mock_tmp,
        patch("app.worker.pipeline.os.unlink"),
    ):
        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/fake.mp3"))
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/fake.mp3"
        await process_recording(ctx, str(rec.id))

    assert RecordingStatus.transcribing in statuses_at_commit
    assert RecordingStatus.embedding in statuses_at_commit
    assert statuses_at_commit[-1] == RecordingStatus.ready
    t_idx = statuses_at_commit.index(RecordingStatus.transcribing)
    r_idx = len(statuses_at_commit) - 1 - statuses_at_commit[::-1].index(RecordingStatus.ready)
    assert t_idx < r_idx


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------


async def test_transcriber_raises_sets_failed_and_reraises():
    """If transcriber throws, status=failed, error_message set, exception re-raised."""
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

    boom_transcriber = MockTranscriber()
    boom_transcriber.transcribe = MagicMock(side_effect=RuntimeError("whisper exploded"))

    storage = _make_storage()

    ctx = {
        "db_session_factory": factory,
        "storage": storage,
        "transcriber": boom_transcriber,
        "embedder": MockEmbedder(),
        "vector_store": MockVectorStore(),
    }

    with (
        patch("app.worker.pipeline.tempfile.NamedTemporaryFile") as mock_tmp,
        patch("app.worker.pipeline.os.unlink"),
        pytest.raises(RuntimeError, match="whisper exploded"),
    ):
        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/fake.mp3"))
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/fake.mp3"
        await process_recording(ctx, str(rec.id))

    assert err_rec.status == RecordingStatus.failed
    assert "whisper exploded" in err_rec.error_message


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


async def test_pipeline_noop_when_recording_not_found():
    factory = _make_session_factory(recording=None)
    storage = _make_storage()
    ctx = {
        "db_session_factory": factory,
        "storage": storage,
        "transcriber": MockTranscriber(),
        "embedder": MockEmbedder(),
        "vector_store": MockVectorStore(),
    }
    # Should not raise
    await process_recording(ctx, str(uuid.uuid4()))
    factory.return_value.commit.assert_not_called()


async def test_empty_transcript_sets_ready_with_no_segments():
    """If transcriber returns [] (silence), status still advances to ready."""
    rec = _make_recording()
    factory = _make_session_factory(rec)
    storage = _make_storage()
    ctx = {
        "db_session_factory": factory,
        "storage": storage,
        "transcriber": MockTranscriber(segments=[]),
        "embedder": MockEmbedder(),
        "vector_store": MockVectorStore(),
    }

    with (
        patch("app.worker.pipeline.tempfile.NamedTemporaryFile") as mock_tmp,
        patch("app.worker.pipeline.os.unlink"),
    ):
        mock_tmp.return_value.__enter__ = MagicMock(return_value=MagicMock(name="/tmp/fake.mp3"))
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/fake.mp3"
        await process_recording(ctx, str(rec.id))

    assert rec.status == RecordingStatus.ready
    assert rec.duration_seconds is None  # no segments to derive duration from
    factory.return_value.add.assert_not_called()
