from datetime import UTC, datetime, timedelta

import pytest
from jose import JWTError, jwt

from app.core.config import settings


def test_hash_password_produces_bcrypt_hash():
    from app.core.security import hash_password

    hashed = hash_password("mypassword123")
    assert hashed != "mypassword123"
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    from app.core.security import hash_password, verify_password

    hashed = hash_password("mypassword123")
    assert verify_password("mypassword123", hashed) is True


def test_verify_password_wrong_password():
    from app.core.security import hash_password, verify_password

    hashed = hash_password("mypassword123")
    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token_encodes_user_id():
    from app.core.security import create_access_token

    token = create_access_token("user-uuid-123")
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "user-uuid-123"


def test_decode_access_token_returns_user_id():
    from app.core.security import create_access_token, decode_access_token

    token = create_access_token("user-uuid-456")
    assert decode_access_token(token) == "user-uuid-456"


def test_decode_garbage_token_raises_jwt_error():
    from app.core.security import decode_access_token

    with pytest.raises(JWTError):
        decode_access_token("not.a.real.token")


def test_decode_expired_token_raises_jwt_error():
    from app.core.security import decode_access_token

    expired_payload = {"sub": "user-id", "exp": datetime.now(UTC) - timedelta(minutes=1)}
    expired_token = jwt.encode(
        expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(JWTError):
        decode_access_token(expired_token)


def test_decode_token_missing_sub_raises_jwt_error():
    from app.core.security import decode_access_token

    bad_token = jwt.encode({"foo": "bar"}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(JWTError):
        decode_access_token(bad_token)
