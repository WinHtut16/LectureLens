"""slowapi rate limiter — shared instance registered with FastAPI app.state."""

from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def _get_user_key(request: Request) -> str:
    """Rate-limit key: user_id from JWT when valid, remote IP as fallback."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = jwt.decode(
                auth[7:], settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            return f"user:{payload['sub']}"
        except (JWTError, KeyError):
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_key)
