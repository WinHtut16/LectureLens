"""Unit tests for app.api.recordings — DB, storage, and ARQ are all mocked."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.deps import get_current_user, get_storage
from app.db.models import Recording, RecordingStatus, SourceType, User
from app.main import app
from app.ml.audio_validator import AudioValidationResult


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_user(email: str = "alice@example.com") -> User:
    u = User()
    u.id = uuid.uuid4()
    u.email = email
    u.password_hash = "irrelevant"
    u.created_at = datetime.now(UTC)
    return u


def _make_recording(user: User, title: str = "lecture.mp3") -> Recording:
    r = Recording()
    r.id = uuid.uuid4()
    r.user_id = user.id
    r.title = title
    r.source_type = SourceType.upload
    r.source_url = None
    r.audio_path = f"audio/{user.id}/{r.id}.mp3"
    r.duration_seconds = None
    r.status = RecordingStatus.queued
    r.error_message = None
    r.created_at = datetime.now(UTC)
    return r


def _mock_storage() -> MagicMock:
    s = MagicMock()
    s.upload_file = AsyncMock(return_value="audio/key")
    s.delete_file = AsyncMock()
    return s


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def alice() -> User:
    return _make_user("alice@example.com")


@pytest.fixture
def bob() -> User:
    return _make_user("bob@example.com")


@pytest.fixture
def mock_storage() -> MagicMock:
    return _mock_storage()


@pytest.fixture(autouse=True)
def inject_storage(mock_storage):
    app.dependency_overrides[get_storage] = lambda: mock_storage


# ---------------------------------------------------------------------------
# POST /api/v1/recordings
# ---------------------------------------------------------------------------

_VALID_RESULT = AudioValidationResult(valid=True, error=None, detected_mime="audio/mpeg")
_INVALID_TYPE = AudioValidationResult(
    valid=False, error="Unsupported file type 'text/plain'", detected_mime="text/plain"
)
_OVERSIZED = AudioValidationResult(
    valid=False, error="File exceeds maximum allowed size of 50 MB", detected_mime=""
)

_MP3_BYTES = b"ID3\x03" + b"\x00" * 100  # real ID3v2 magic header


async def test_upload_valid_file_returns_201_queued(client: AsyncClient, alice: User):
    app.dependency_overrides[get_current_user] = lambda: alice
    rec = _make_recording(alice)

    with (
        patch("app.api.recordings.validate_audio", return_value=_VALID_RESULT),
        patch("app.api.recordings.svc.create_recording", new_callable=AsyncMock, return_value=rec),
        patch("app.api.recordings._get_arq_pool", new_callable=AsyncMock) as mock_pool_fn,
    ):
        mock_pool = AsyncMock()
        mock_pool_fn.return_value = mock_pool

        resp = await client.post(
            "/api/v1/recordings",
            files={"file": ("lecture.mp3", _MP3_BYTES, "audio/mpeg")},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "queued"
    mock_pool.enqueue_job.assert_called_once_with("process_recording", str(rec.id))


async def test_upload_invalid_file_type_returns_415(client: AsyncClient, alice: User):
    app.dependency_overrides[get_current_user] = lambda: alice

    with patch("app.api.recordings.validate_audio", return_value=_INVALID_TYPE):
        resp = await client.post(
            "/api/v1/recordings",
            files={"file": ("not_audio.mp3", b"Hello, world!", "text/plain")},
        )

    assert resp.status_code == 415
    assert resp.json()["detail"]["code"] == "unsupported_media_type"


async def test_upload_oversized_file_returns_413(client: AsyncClient, alice: User):
    app.dependency_overrides[get_current_user] = lambda: alice

    with patch("app.api.recordings.validate_audio", return_value=_OVERSIZED):
        resp = await client.post(
            "/api/v1/recordings",
            files={"file": ("big.mp3", b"x" * 10, "audio/mpeg")},
        )

    assert resp.status_code == 413
    assert resp.json()["detail"]["code"] == "file_too_large"


async def test_upload_no_auth_returns_401(client: AsyncClient):
    resp = await client.post(
        "/api/v1/recordings",
        files={"file": ("lecture.mp3", _MP3_BYTES, "audio/mpeg")},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/recordings
# ---------------------------------------------------------------------------


async def test_list_recordings_returns_only_current_users(client: AsyncClient, alice: User):
    app.dependency_overrides[get_current_user] = lambda: alice
    recs = [_make_recording(alice, "a.mp3"), _make_recording(alice, "b.mp3")]

    with patch(
        "app.api.recordings.svc.list_recordings", new_callable=AsyncMock, return_value=recs
    ):
        resp = await client.get("/api/v1/recordings")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_recordings_no_auth_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/recordings")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/recordings/{id}
# ---------------------------------------------------------------------------


async def test_get_recording_returns_200(client: AsyncClient, alice: User):
    app.dependency_overrides[get_current_user] = lambda: alice
    rec = _make_recording(alice)

    with patch(
        "app.api.recordings.svc.get_recording", new_callable=AsyncMock, return_value=rec
    ):
        resp = await client.get(f"/api/v1/recordings/{rec.id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(rec.id)


async def test_get_recording_other_user_returns_403(client: AsyncClient, alice: User):
    from fastapi import HTTPException

    app.dependency_overrides[get_current_user] = lambda: alice

    with patch(
        "app.api.recordings.svc.get_recording",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=403, detail="Access denied"),
    ):
        resp = await client.get(f"/api/v1/recordings/{uuid.uuid4()}")

    assert resp.status_code == 403


async def test_get_recording_not_found_returns_404(client: AsyncClient, alice: User):
    from fastapi import HTTPException

    app.dependency_overrides[get_current_user] = lambda: alice

    with patch(
        "app.api.recordings.svc.get_recording",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=404, detail="Recording not found"),
    ):
        resp = await client.get(f"/api/v1/recordings/{uuid.uuid4()}")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/recordings/{id}/status
# ---------------------------------------------------------------------------


async def test_status_poll_returns_current_status(client: AsyncClient, alice: User):
    app.dependency_overrides[get_current_user] = lambda: alice
    rec = _make_recording(alice)
    rec.status = RecordingStatus.transcribing

    with patch(
        "app.api.recordings.svc.get_recording_status", new_callable=AsyncMock, return_value=rec
    ):
        resp = await client.get(f"/api/v1/recordings/{rec.id}/status")

    assert resp.status_code == 200
    assert resp.json()["status"] == "transcribing"
    assert resp.json()["id"] == str(rec.id)


# ---------------------------------------------------------------------------
# DELETE /api/v1/recordings/{id}
# ---------------------------------------------------------------------------


async def test_delete_own_recording_returns_204(client: AsyncClient, alice: User):
    app.dependency_overrides[get_current_user] = lambda: alice
    rec = _make_recording(alice)

    with patch("app.api.recordings.svc.delete_recording", new_callable=AsyncMock):
        resp = await client.delete(f"/api/v1/recordings/{rec.id}")

    assert resp.status_code == 204


async def test_delete_other_users_recording_returns_403(client: AsyncClient, alice: User):
    from fastapi import HTTPException

    app.dependency_overrides[get_current_user] = lambda: alice

    with patch(
        "app.api.recordings.svc.delete_recording",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=403, detail="Access denied"),
    ):
        resp = await client.delete(f"/api/v1/recordings/{uuid.uuid4()}")

    assert resp.status_code == 403


async def test_delete_no_auth_returns_401(client: AsyncClient):
    resp = await client.delete(f"/api/v1/recordings/{uuid.uuid4()}")
    assert resp.status_code == 401
