"""Background processing pipeline.

process_recording is an ARQ task. It receives a recording_id, advances
Recording.status through the pipeline stages, and marks the job failed on
any unhandled exception.

ctx must contain:
  - "transcriber": TranscriberProtocol  (injected by WorkerSettings.on_startup)
  - "storage": StorageClient            (injected by WorkerSettings.on_startup)
  - "db_session_factory": optional — if absent, creates its own (needed for tests)
"""

import asyncio
import logging
import os
import tempfile
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.storage import StorageClient
from app.db.models import Recording, RecordingStatus, Segment
from app.ml.chunker import chunk_segments
from app.ml.transcriber import TranscriberProtocol

logger = logging.getLogger(__name__)


def _make_session() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def process_recording(ctx: dict[str, Any], recording_id: str) -> None:
    """ARQ task: run the full processing pipeline for one recording."""
    SessionLocal = ctx.get("db_session_factory") or _make_session()
    transcriber: TranscriberProtocol = ctx["transcriber"]
    storage: StorageClient = ctx["storage"]
    rec_uuid = uuid.UUID(recording_id)

    async with SessionLocal() as session:
        try:
            recording = await session.scalar(select(Recording).where(Recording.id == rec_uuid))
            if recording is None:
                logger.error("process_recording: recording %s not found", recording_id)
                return

            # ── Stage 1: transcription ──────────────────────────────────────
            recording.status = RecordingStatus.transcribing
            await session.commit()

            audio_bytes = await storage.download_file(recording.audio_path)
            suffix = "." + recording.audio_path.rsplit(".", 1)[-1]

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                raw_segments = await asyncio.to_thread(transcriber.transcribe, tmp_path)
            finally:
                os.unlink(tmp_path)

            # ── Chunking + persistence ──────────────────────────────────────
            chunks = chunk_segments(raw_segments)
            for idx, chunk in enumerate(chunks):
                session.add(
                    Segment(
                        recording_id=rec_uuid,
                        start_seconds=chunk.start,
                        end_seconds=chunk.end,
                        text=chunk.text,
                        speaker_label=None,
                        segment_index=idx,
                    )
                )

            if raw_segments:
                recording.duration_seconds = int(raw_segments[-1].end)

            # ── Advance to ready ────────────────────────────────────────────
            recording.status = RecordingStatus.ready
            await session.commit()

            logger.info("process_recording: %s → ready", recording_id)

        except Exception as exc:
            logger.exception("process_recording: %s failed", recording_id)
            await session.rollback()
            async with SessionLocal() as err_session:
                failed_rec = await err_session.scalar(
                    select(Recording).where(Recording.id == rec_uuid)
                )
                if failed_rec is not None:
                    failed_rec.status = RecordingStatus.failed
                    failed_rec.error_message = str(exc)
                    await err_session.commit()
            raise
