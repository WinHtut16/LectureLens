"""Unit tests for POST /api/v1/recordings/{id}/search."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_current_user, get_db, get_embedder, get_vector_store
from app.db.models import Recording, RecordingStatus, SourceType, User
from app.main import app
from app.ml.embedder import MockEmbedder
from app.ml.vector_store import MockVectorStore
from app.services.search_service import SearchHit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(email: str = "alice@example.com") -> User:
    u = User()
    u.id = uuid.uuid4()
    u.email = email
    u.password_hash = "x"
    u.created_at = datetime.now(UTC)
    return u


def _make_recording(user: User, status: RecordingStatus = RecordingStatus.ready) -> Recording:
    r = Recording()
    r.id = uuid.uuid4()
    r.user_id = user.id
    r.title = "lecture.mp3"
    r.source_type = SourceType.upload
    r.source_url = None
    r.audio_path = f"audio/{user.id}/{r.id}.mp3"
    r.duration_seconds = 60
    r.status = status
    r.error_message = None
    r.created_at = datetime.now(UTC)
    r.segments = []
    return r


_EMPTY_HIT_RESULT: tuple[list[SearchHit], float] = ([], 42.0)

_ONE_HIT_RESULT: tuple[list[SearchHit], float] = (
    [
        SearchHit(
            segment_id=str(uuid.uuid4()),
            start_seconds=5.0,
            end_seconds=35.0,
            text="gradient descent is an optimization algorithm",
            score=0.91,
            speaker_label=None,
        )
    ],
    42.0,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def alice() -> User:
    return _make_user("alice@example.com")


@pytest.fixture
def bob() -> User:
    return _make_user("bob@example.com")


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture(autouse=True)
def inject_ml_mocks():
    app.dependency_overrides[get_embedder] = lambda: MockEmbedder()
    app.dependency_overrides[get_vector_store] = lambda: MockVectorStore()


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


async def test_no_auth_returns_401(client: AsyncClient, mock_db: AsyncMock):
    app.dependency_overrides[get_db] = lambda: mock_db
    rec_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/recordings/{rec_id}/search",
        json={"query": "hello"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


async def test_query_too_long_returns_422(client: AsyncClient, mock_db: AsyncMock, alice: User):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: alice

    resp = await client.post(
        f"/api/v1/recordings/{uuid.uuid4()}/search",
        json={"query": "x" * 257},
    )
    assert resp.status_code == 422


async def test_k_above_20_returns_422(client: AsyncClient, mock_db: AsyncMock, alice: User):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: alice

    resp = await client.post(
        f"/api/v1/recordings/{uuid.uuid4()}/search",
        json={"query": "hello", "k": 21},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Service-level errors forwarded correctly
# ---------------------------------------------------------------------------


async def test_wrong_user_returns_403(client: AsyncClient, mock_db: AsyncMock, bob: User):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: bob
    rec_id = uuid.uuid4()

    with patch(
        "app.api.recordings.search_svc.search_recording",
        new_callable=AsyncMock,
        side_effect=HTTPException(
            status_code=403,
            detail={"code": "forbidden", "message": "Access denied"},
        ),
    ):
        resp = await client.post(
            f"/api/v1/recordings/{rec_id}/search",
            json={"query": "hello"},
        )
    assert resp.status_code == 403


async def test_recording_not_ready_returns_400(
    client: AsyncClient, mock_db: AsyncMock, alice: User
):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: alice
    rec_id = uuid.uuid4()

    with patch(
        "app.api.recordings.search_svc.search_recording",
        new_callable=AsyncMock,
        side_effect=HTTPException(
            status_code=400,
            detail={"code": "not_indexed", "message": "Recording is not yet indexed"},
        ),
    ):
        resp = await client.post(
            f"/api/v1/recordings/{rec_id}/search",
            json={"query": "hello"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "not_indexed"


# ---------------------------------------------------------------------------
# Happy path shape
# ---------------------------------------------------------------------------


async def test_search_returns_results_and_query_time(
    client: AsyncClient, mock_db: AsyncMock, alice: User
):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: alice

    with patch(
        "app.api.recordings.search_svc.search_recording",
        new_callable=AsyncMock,
        return_value=_ONE_HIT_RESULT,
    ):
        resp = await client.post(
            f"/api/v1/recordings/{uuid.uuid4()}/search",
            json={"query": "gradient descent"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body
    assert "query_time_ms" in body
    assert len(body["results"]) == 1
    hit = body["results"][0]
    assert hit["start_seconds"] == pytest.approx(5.0)
    assert hit["text"] == "gradient descent is an optimization algorithm"
    assert hit["score"] == pytest.approx(0.91, abs=1e-4)
