"""Recordings service — all business logic, no HTTP concerns."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.storage import StorageClient
from app.db.models import Recording, RecordingStatus, SourceType


async def create_recording(
    db: AsyncSession,
    *,
    id: uuid.UUID | None = None,
    user_id: uuid.UUID,
    title: str,
    audio_path: str,
    source_type: SourceType = SourceType.upload,
    source_url: str | None = None,
) -> Recording:
    recording = Recording(
        id=id or uuid.uuid4(),
        user_id=user_id,
        title=title,
        audio_path=audio_path,
        source_type=source_type,
        source_url=source_url,
        status=RecordingStatus.queued,
    )
    db.add(recording)
    await db.commit()
    await db.refresh(recording)
    return recording


async def list_recordings(db: AsyncSession, *, user_id: uuid.UUID) -> list[Recording]:
    result = await db.execute(
        select(Recording).where(Recording.user_id == user_id).order_by(Recording.created_at.desc())
    )
    return list(result.scalars().all())


async def get_recording(
    db: AsyncSession, *, recording_id: uuid.UUID, user_id: uuid.UUID
) -> Recording:
    recording = await db.scalar(
        select(Recording)
        .where(Recording.id == recording_id)
        .options(selectinload(Recording.segments))
    )
    if recording is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")
    if recording.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return recording


async def get_recording_status(
    db: AsyncSession, *, recording_id: uuid.UUID, user_id: uuid.UUID
) -> Recording:
    return await get_recording(db, recording_id=recording_id, user_id=user_id)


async def delete_recording(
    db: AsyncSession,
    *,
    recording_id: uuid.UUID,
    user_id: uuid.UUID,
    storage: StorageClient,
) -> None:
    recording = await get_recording(db, recording_id=recording_id, user_id=user_id)
    audio_path = recording.audio_path
    await db.delete(recording)
    await db.commit()
    await storage.delete_file(audio_path)
