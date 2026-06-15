"""LectureLens API entrypoint."""

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.auth import router as auth_router
from app.api.recordings import router as recordings_router
from app.core.config import settings
from app.core.limiter import limiter

app = FastAPI(title="LectureLens API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(recordings_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
