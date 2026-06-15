"""ARQ WorkerSettings — wires Redis connection and registers task functions."""

from typing import Any

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.storage import make_storage_client
from app.ml.transcriber import FasterWhisperTranscriber
from app.worker.pipeline import _make_session, process_recording


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [process_recording]

    @staticmethod
    async def on_startup(ctx: dict[str, Any]) -> None:
        from app.ml.embedder import Embedder
        from app.ml.vector_store import VectorStore

        ctx["transcriber"] = FasterWhisperTranscriber(model_size=settings.WHISPER_MODEL_SIZE)
        ctx["storage"] = make_storage_client(settings)
        ctx["db_session_factory"] = _make_session()
        ctx["embedder"] = Embedder()
        # Worker keeps an in-memory VectorStore; pipeline adds segments then
        # saves per-recording index files to FAISS_INDEX_PATH for the API to load.
        ctx["vector_store"] = VectorStore()
