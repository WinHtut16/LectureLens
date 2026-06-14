"""Background processing pipeline.

process_recording is an ARQ task. It receives a recording_id, advances the
Recording.status through the pipeline stages, and marks the job failed on
any unhandled exception.

Slice 3 (stub): sets transcribing → sleeps 2 s → sets ready.
Real Whisper/embedding stages land in Slice 4.
"""

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models import Recording, RecordingStatus

logger = logging.getLogger(__name__)


def _make_session() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def process_recording(ctx: dict[str, Any], recording_id: str) -> None:
    """ARQ task: run the processing pipeline for one recording."""
    SessionLocal = ctx.get("db_session_factory") or _make_session()
    rec_uuid = uuid.UUID(recording_id)

    async with SessionLocal() as session:
        try:
            recording = await session.scalar(select(Recording).where(Recording.id == rec_uuid))
            if recording is None:
                logger.error("process_recording: recording %s not found", recording_id)
                return

            # Stage 1: transcription (stub — real Whisper in Slice 4)
            recording.status = RecordingStatus.transcribing
            await session.commit()

            await asyncio.sleep(2)

            # Future stages (diarizing, embedding) will be inserted here.

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
