from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# Computed once at import time; used as a timing-safe dummy so login always
# pays bcrypt cost even when the email doesn't exist (prevents user enumeration).
_DUMMY_HASH: str = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return str(
        jwt.encode(
            {"sub": user_id, "exp": expire},
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
    )


def decode_access_token(token: str) -> str:
    """Return the user_id (sub claim). Raises JWTError on bad signature, expiry, or missing sub."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    sub: str | None = payload.get("sub")
    if sub is None:
        raise JWTError("missing sub claim")
    return sub
