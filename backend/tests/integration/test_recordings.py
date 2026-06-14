"""Integration tests for the recordings slice.

Uses a real Postgres database (docker-compose locally; GH Actions service in CI).
Storage is patched to LocalStorageClient (tmp_path) — we don't want to hit real S3.
ARQ enqueue is patched — we don't want to hit real Redis or run the worker.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.deps import get_storage
from app.core.storage import LocalStorageClient
from app.main import app
from app.ml.audio_validator import AudioValidationResult

# Real ID3v2 magic bytes so validate_audio accepts the file
_MP3_BYTES = b"ID3\x03" + b"\x00" * 200

_VALID_RESULT = AudioValidationResult(valid=True, error=None, detected_mime="audio/mpeg")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _signup_and_token(client: AsyncClient, email: str, password: str = "password1234") -> str:
    resp = await client.post(
        "/api/v1/auth/signup", json={"email": email, "password": password}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _upload(client: AsyncClient, token: str, filename: str = "lecture.mp3") -> dict:
    """Upload a recording, mocking validate_audio and the ARQ pool."""
    with (
        patch("app.api.recordings.validate_audio", return_value=_VALID_RESULT),
        patch("app.api.recordings._get_arq_pool", new_callable=AsyncMock) as mock_pool_fn,
    ):
        mock_pool = AsyncMock()
        mock_pool_fn.return_value = mock_pool
        resp = await client.post(
            "/api/v1/recordings",
            files={"file": (filename, _MP3_BYTES, "audio/mpeg")},
            headers=_auth(token),
        )
    return resp.json(), resp.status_code


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def inject_local_storage(tmp_path):
    storage = LocalStorageClient(base_path=str(tmp_path))
    app.dependency_overrides[get_storage] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage, None)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


async def test_upload_creates_recording_with_queued_status(http_client: AsyncClient):
    token = await _signup_and_token(http_client, "alice@test.com")
    data, status_code = await _upload(http_client, token, "lecture.mp3")

    assert status_code == 201
    assert data["status"] == "queued"
    assert data["title"] == "lecture.mp3"
    assert uuid.UUID(data["id"])  # valid UUID


async def test_upload_no_auth_returns_401(http_client: AsyncClient):
    with patch("app.api.recordings.validate_audio", return_value=_VALID_RESULT):
        resp = await http_client.post(
            "/api/v1/recordings",
            files={"file": ("x.mp3", _MP3_BYTES, "audio/mpeg")},
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List — user isolation
# ---------------------------------------------------------------------------


async def test_list_returns_only_current_users_recordings(http_client: AsyncClient):
    """Alice and Bob each upload a recording; they must not see each other's."""
    alice_token = await _signup_and_token(http_client, "alice@iso.com")
    bob_token = await _signup_and_token(http_client, "bob@iso.com")

    await _upload(http_client, alice_token, "alice.mp3")
    await _upload(http_client, bob_token, "bob.mp3")

    alice_resp = await http_client.get("/api/v1/recordings", headers=_auth(alice_token))
    bob_resp = await http_client.get("/api/v1/recordings", headers=_auth(bob_token))

    alice_titles = {r["title"] for r in alice_resp.json()}
    bob_titles = {r["title"] for r in bob_resp.json()}

    assert alice_titles == {"alice.mp3"}
    assert bob_titles == {"bob.mp3"}
    # No cross-contamination
    assert "bob.mp3" not in alice_titles
    assert "alice.mp3" not in bob_titles


# ---------------------------------------------------------------------------
# GET detail — IDOR guard
# ---------------------------------------------------------------------------


async def test_get_own_recording_returns_200(http_client: AsyncClient):
    token = await _signup_and_token(http_client, "getme@test.com")
    data, _ = await _upload(http_client, token, "mine.mp3")
    rec_id = data["id"]

    resp = await http_client.get(f"/api/v1/recordings/{rec_id}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == rec_id


async def test_get_other_users_recording_returns_403(http_client: AsyncClient):
    alice_token = await _signup_and_token(http_client, "idor_alice@test.com")
    bob_token = await _signup_and_token(http_client, "idor_bob@test.com")

    alice_data, _ = await _upload(http_client, alice_token, "alices_secret.mp3")
    alice_rec_id = alice_data["id"]

    # Bob tries to access Alice's recording
    resp = await http_client.get(
        f"/api/v1/recordings/{alice_rec_id}", headers=_auth(bob_token)
    )
    assert resp.status_code == 403


async def test_get_nonexistent_recording_returns_404(http_client: AsyncClient):
    token = await _signup_and_token(http_client, "missing@test.com")
    resp = await http_client.get(
        f"/api/v1/recordings/{uuid.uuid4()}", headers=_auth(token)
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Status poll
# ---------------------------------------------------------------------------


async def test_status_poll_returns_queued_immediately_after_upload(http_client: AsyncClient):
    token = await _signup_and_token(http_client, "poll@test.com")
    data, _ = await _upload(http_client, token)
    rec_id = data["id"]

    resp = await http_client.get(
        f"/api/v1/recordings/{rec_id}/status", headers=_auth(token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == rec_id
    assert body["status"] == "queued"


# ---------------------------------------------------------------------------
# Delete — IDOR guard
# ---------------------------------------------------------------------------


async def test_delete_own_recording_returns_204_and_removes_from_list(http_client: AsyncClient):
    token = await _signup_and_token(http_client, "del@test.com")
    data, _ = await _upload(http_client, token, "todelete.mp3")
    rec_id = data["id"]

    resp = await http_client.delete(
        f"/api/v1/recordings/{rec_id}", headers=_auth(token)
    )
    assert resp.status_code == 204

    list_resp = await http_client.get("/api/v1/recordings", headers=_auth(token))
    ids = [r["id"] for r in list_resp.json()]
    assert rec_id not in ids


async def test_delete_other_users_recording_returns_403(http_client: AsyncClient):
    alice_token = await _signup_and_token(http_client, "del_alice@test.com")
    bob_token = await _signup_and_token(http_client, "del_bob@test.com")

    alice_data, _ = await _upload(http_client, alice_token, "protected.mp3")
    alice_rec_id = alice_data["id"]

    # Bob tries to delete Alice's recording
    resp = await http_client.delete(
        f"/api/v1/recordings/{alice_rec_id}", headers=_auth(bob_token)
    )
    assert resp.status_code == 403

    # Alice's recording still exists
    check = await http_client.get(
        f"/api/v1/recordings/{alice_rec_id}", headers=_auth(alice_token)
    )
    assert check.status_code == 200
