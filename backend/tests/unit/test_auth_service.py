import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.db.models import User


def _make_user(email: str = "user@example.com") -> User:
    u = User()
    u.id = uuid.uuid4()
    u.email = email
    u.password_hash = "$2b$12$irrelevant"
    u.created_at = datetime.now(UTC)
    return u


# ---- signup ----

@pytest.mark.asyncio
async def test_signup_happy_path_returns_token_and_user():
    from app.services.auth import signup

    db = AsyncMock()
    db.scalar.return_value = None  # no existing user

    with (
        patch("app.services.auth.hash_password", return_value="hashed_pw"),
        patch("app.services.auth.create_access_token", return_value="tok123"),
    ):
        token, user = await signup("new@example.com", "validpassword1", db)

    assert token == "tok123"
    assert user.email == "new@example.com"
    assert user.password_hash == "hashed_pw"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_signup_duplicate_email_raises_400():
    from app.services.auth import signup

    db = AsyncMock()
    db.scalar.return_value = _make_user()  # existing user found

    with pytest.raises(HTTPException) as exc_info:
        await signup("taken@example.com", "validpassword1", db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "email_taken"


# ---- login ----

@pytest.mark.asyncio
async def test_login_correct_credentials_returns_token_and_user():
    from app.services.auth import login

    existing = _make_user()
    db = AsyncMock()
    db.scalar.return_value = existing

    with (
        patch("app.services.auth.verify_password", return_value=True),
        patch("app.services.auth.create_access_token", return_value="tok456"),
    ):
        token, user = await login("user@example.com", "correctpassword", db)

    assert token == "tok456"
    assert user is existing


@pytest.mark.asyncio
async def test_login_wrong_password_raises_401():
    from app.services.auth import login

    db = AsyncMock()
    db.scalar.return_value = _make_user()

    with patch("app.services.auth.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await login("user@example.com", "wrongpassword", db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_login_nonexistent_email_raises_401():
    from app.services.auth import login

    db = AsyncMock()
    db.scalar.return_value = None

    with patch("app.services.auth.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await login("ghost@example.com", "anypassword", db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email_and_wrong_password_return_identical_error():
    from app.services.auth import login

    # Case 1: user not found
    db = AsyncMock()
    db.scalar.return_value = None
    with patch("app.services.auth.verify_password", return_value=False):
        with pytest.raises(HTTPException) as not_found_exc:
            await login("ghost@example.com", "pass", db)

    # Case 2: wrong password
    db.scalar.return_value = _make_user()
    with patch("app.services.auth.verify_password", return_value=False):
        with pytest.raises(HTTPException) as wrong_pw_exc:
            await login("user@example.com", "wrong", db)

    assert not_found_exc.value.status_code == wrong_pw_exc.value.status_code
    assert not_found_exc.value.detail == wrong_pw_exc.value.detail
