"""Integration test: upload → run pipeline (mocked ML) → search via API.

Uses a real Postgres database. ML is mocked (MockTranscriber + MockEmbedder)
so the test is fast and deterministic. The VectorStore is a real in-memory
FAISS instance shared between the pipeline and the API via dependency override.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.deps import get_embedder, get_storage, get_vector_store
from app.db.models import RecordingStatus
from app.main import app
from app.ml.audio_validator import AudioValidationResult
from app.ml.embedder import MockEmbedder
from app.ml.transcriber import MockTranscriber, TranscriptSegment
from app.ml.vector_store import VectorStore
from app.worker.pipeline import process_recording

_MP3_BYTES = b"ID3\x03" + b"\x00" * 200
_VALID_RESULT = AudioValidationResult(valid=True, error=None, detected_mime="audio/mpeg")

_SEGMENTS = [
    TranscriptSegment(start=0.0, end=15.0, text="introduction to machine learning"),
    TranscriptSegment(start=15.0, end=30.0, text="gradient descent optimization algorithm"),
]


async def _signup_and_token(client: AsyncClient, email: str) -> str:
    resp = await client.post("/api/v1/auth/signup", json={"email": email, "password": "pass1234"})
    assert resp.status_code == 201
    return resp.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _upload_recording(client: AsyncClient, token: str) -> str:
    with (
        patch("app.api.recordings.validate_audio", return_value=_VALID_RESULT),
        patch("app.api.recordings._get_arq_pool", new_callable=AsyncMock) as mock_pool_fn,
    ):
        mock_pool = AsyncMock()
        mock_pool_fn.return_value = mock_pool
        resp = await client.post(
            "/api/v1/recordings",
            files={"file": ("lecture.mp3", _MP3_BYTES, "audio/mpeg")},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
async def search_test_setup(tmp_path):
    """Yields (http_client, token, recording_id, shared_vector_store)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.storage import LocalStorageClient

    storage = LocalStorageClient(base_path=str(tmp_path))
    emb = MockEmbedder()
    vs = VectorStore()  # shared between pipeline and API

    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_embedder] = lambda: emb
    app.dependency_overrides[get_vector_store] = lambda: vs

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _signup_and_token(client, "search_int@test.com")
        recording_id = await _upload_recording(client, token)

        engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        SessionFactory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        ctx = {
            "db_session_factory": SessionFactory,
            "storage": storage,
            "transcriber": MockTranscriber(segments=_SEGMENTS),
            "embedder": emb,
            "vector_store": vs,
        }
        await process_recording(ctx, recording_id)
        await engine.dispose()

        yield client, token, recording_id, vs

    app.dependency_overrides.pop(get_storage, None)
    app.dependency_overrides.pop(get_embedder, None)
    app.dependency_overrides.pop(get_vector_store, None)


async def test_search_returns_results_after_pipeline(search_test_setup):
    client, token, recording_id, vs = search_test_setup

    resp = await client.post(
        f"/api/v1/recordings/{recording_id}/search",
        json={"query": "machine learning basics", "k": 5},
        headers=_auth(token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) >= 1
    for hit in body["results"]:
        assert hit["start_seconds"] >= 0.0
        assert hit["score"] >= 0.0
        assert hit["text"]
    assert body["query_time_ms"] < 800  # SPEC §9: p95 < 800 ms


async def test_search_cross_user_isolation(search_test_setup):
    """Bob cannot search Alice's recording."""
    client, alice_token, recording_id, _ = search_test_setup

    bob_token = await _signup_and_token(client, "bob_search_int@test.com")
    resp = await client.post(
        f"/api/v1/recordings/{recording_id}/search",
        json={"query": "machine learning"},
        headers=_auth(bob_token),
    )
    assert resp.status_code == 403


async def test_search_recording_not_found_returns_404(search_test_setup):
    client, token, _, _ = search_test_setup

    resp = await client.post(
        f"/api/v1/recordings/{uuid.uuid4()}/search",
        json={"query": "anything"},
        headers=_auth(token),
    )
    assert resp.status_code == 404


async def test_speaker_label_filter_returns_subset(search_test_setup):
    """speaker_label filter: with no diarization, all segments have speaker_label=None,
    so filtering by a non-null label returns an empty result."""
    client, token, recording_id, _ = search_test_setup

    resp = await client.post(
        f"/api/v1/recordings/{recording_id}/search",
        json={"query": "gradient descent", "speaker_label": "Speaker 1"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["results"] == []
