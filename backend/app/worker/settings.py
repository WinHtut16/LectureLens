"""ARQ WorkerSettings — wires Redis connection and registers task functions."""

from arq.connections import RedisSettings

from app.core.config import settings
from app.worker.pipeline import process_recording


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [process_recording]
