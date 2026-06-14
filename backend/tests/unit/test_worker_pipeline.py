"""Unit tests for app.worker.pipeline — all DB ops mocked."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models import Recording, RecordingStatus
from app.worker.pipeline import process_recording


def _make_recording(status: RecordingStatus = RecordingStatus.queued) -> MagicMock:
    rec = MagicMock(spec=Recording)
    rec.id = uuid.uuid4()
    rec.status = status
    return rec


def _make_session_factory(recording: MagicMock | None) -> MagicMock:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=recording)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock()
    factory.return_value = session
    return factory


async def test_pipeline_transitions_queued_to_ready():
    rec = _make_recording()
    factory = _make_session_factory(rec)

    with patch("app.worker.pipeline.asyncio.sleep", new=AsyncMock()):
        await process_recording({"db_session_factory": factory}, str(rec.id))

    # First commit should set transcribing, second should set ready
    assert rec.status == RecordingStatus.ready
    assert factory.return_value.commit.call_count == 2


async def test_pipeline_sets_transcribing_before_ready():
    statuses: list[RecordingStatus] = []
    rec = _make_recording()

    original_commit = AsyncMock()

    async def capture_commit():
        statuses.append(rec.status)
        await original_commit()

    factory = _make_session_factory(rec)
    factory.return_value.commit = capture_commit

    with patch("app.worker.pipeline.asyncio.sleep", new=AsyncMock()):
        await process_recording({"db_session_factory": factory}, str(rec.id))

    assert RecordingStatus.transcribing in statuses
    assert statuses[-1] == RecordingStatus.ready


async def test_pipeline_sets_failed_on_exception():
    rec = _make_recording()

    # First session raises; second session (error handler) sees the same rec
    err_rec = _make_recording()
    err_rec.id = rec.id

    main_session = AsyncMock()
    main_session.scalar = AsyncMock(return_value=rec)
    main_session.commit = AsyncMock(side_effect=[None, RuntimeError("boom")])
    main_session.rollback = AsyncMock()
    main_session.__aenter__ = AsyncMock(return_value=main_session)
    main_session.__aexit__ = AsyncMock(return_value=False)

    err_session = AsyncMock()
    err_session.scalar = AsyncMock(return_value=err_rec)
    err_session.commit = AsyncMock()
    err_session.__aenter__ = AsyncMock(return_value=err_session)
    err_session.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(side_effect=[main_session, err_session])

    with patch("app.worker.pipeline.asyncio.sleep", new=AsyncMock()):
        await process_recording({"db_session_factory": factory}, str(rec.id))

    assert err_rec.status == RecordingStatus.failed
    assert err_rec.error_message == "boom"


async def test_pipeline_is_noop_when_recording_not_found():
    factory = _make_session_factory(recording=None)

    with patch("app.worker.pipeline.asyncio.sleep", new=AsyncMock()):
        # Should not raise
        await process_recording({"db_session_factory": factory}, str(uuid.uuid4()))

    factory.return_value.commit.assert_not_called()
