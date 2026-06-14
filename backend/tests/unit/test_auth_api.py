import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.models import User
from app.main import app


def _make_user(email: str = "test@example.com") -> User:
    u = User()
    u.id = uuid.uuid4()
    u.email = email
    u.password_hash = "irrelevant"
    u.created_at = datetime.now(UTC)
    return u


# ---- /signup ----

@pytest.mark.asyncio
async def test_signup_returns_201_with_token_and_no_password_fields(client: AsyncClient):
    user = _make_user(email="new@example.com")
    with patch("app.api.auth.auth_service.signup", new_callable=AsyncMock, return_value=("tok123", user)):
        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "new@example.com", "password": "validpassword1"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["token"] == "tok123"
    assert data["user"]["email"] == "new@example.com"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_400(client: AsyncClient):
    err = HTTPException(
        status_code=400,
        detail={"code": "email_taken", "message": "Email already registered"},
    )
    with patch("app.api.auth.auth_service.signup", new_callable=AsyncMock, side_effect=err):
        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "taken@example.com", "password": "validpassword1"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "email_taken"


@pytest.mark.asyncio
async def test_signup_password_under_10_chars_returns_422(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "new@example.com", "password": "short"},
    )
    assert resp.status_code == 422


# ---- /login ----

@pytest.mark.asyncio
async def test_login_returns_200_with_token(client: AsyncClient):
    user = _make_user()
    with patch("app.api.auth.auth_service.login", new_callable=AsyncMock, return_value=("tok456", user)):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "correctpassword"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] == "tok456"
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401_generic_message(client: AsyncClient):
    err = HTTPException(
        status_code=401,
        detail={"code": "invalid_credentials", "message": "Invalid credentials"},
    )
    with patch("app.api.auth.auth_service.login", new_callable=AsyncMock, side_effect=err):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
    assert resp.status_code == 401
    assert resp.json()["detail"]["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_nonexistent_email_returns_401_same_message(client: AsyncClient):
    err = HTTPException(
        status_code=401,
        detail={"code": "invalid_credentials", "message": "Invalid credentials"},
    )
    with patch("app.api.auth.auth_service.login", new_callable=AsyncMock, side_effect=err):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "anypassword"},
        )
    assert resp.status_code == 401
    assert resp.json()["detail"]["message"] == "Invalid credentials"


# ---- /me ----

@pytest.mark.asyncio
async def test_me_valid_token_returns_200_and_user_without_password_hash(client: AsyncClient):
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer any.valid.structure"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert "password_hash" not in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_me_no_token_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token_returns_401(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_expired_token_returns_401(client: AsyncClient):
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(
        expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401
