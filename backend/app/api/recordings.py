"""Recordings API — upload, list, detail, status poll, delete."""

import uuid
from datetime import datetime
from typing import Annotated

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_embedder, get_storage, get_vector_store
from app.core.limiter import limiter
from app.core.storage import StorageClient
from app.db.models import Recording, RecordingStatus, SourceType, User
from app.db.session import get_db
from app.ml.audio_validator import validate_audio
from app.ml.embedder import EmbedderProtocol
from app.ml.vector_store import VectorStoreProtocol
from app.services import recordings as svc
from app.services import search_service as search_svc

router = APIRouter(prefix="/recordings", tags=["recordings"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RecordingCreatedResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: RecordingStatus

    model_config = {"from_attributes": True}


class RecordingListItem(BaseModel):
    id: uuid.UUID
    title: str
    status: RecordingStatus
    duration_seconds: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SegmentResponse(BaseModel):
    id: uuid.UUID
    start_seconds: float
    end_seconds: float
    text: str
    speaker_label: str | None
    segment_index: int

    model_config = {"from_attributes": True}


class RecordingDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    source_type: SourceType
    source_url: str | None
    status: RecordingStatus
    duration_seconds: int | None
    error_message: str | None
    created_at: datetime
    segments: list[SegmentResponse]

    model_config = {"from_attributes": True}


class RecordingStatusResponse(BaseModel):
    id: uuid.UUID
    status: RecordingStatus
    error_message: str | None

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: Annotated[str, Field(min_length=1, max_length=256)]
    k: Annotated[int, Field(ge=1, le=20)] = 10
    speaker_label: str | None = None


class SearchHitResponse(BaseModel):
    segment_id: str
    start_seconds: float
    end_seconds: float
    text: str
    score: float
    speaker_label: str | None


class SearchResponse(BaseModel):
    results: list[SearchHitResponse]
    query_time_ms: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_arq_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))


def _storage_key(user_id: uuid.UUID, recording_id: uuid.UUID, filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"audio/{user_id}/{recording_id}.{suffix}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RecordingCreatedResponse)
async def upload_recording(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageClient = Depends(get_storage),
) -> Recording:
    data = await file.read()

    result = validate_audio(data, max_bytes=settings.MAX_UPLOAD_BYTES)
    if not result.valid:
        if "exceeds maximum" in (result.error or ""):
            raise HTTPException(
                status_code=413,
                detail={"code": "file_too_large", "message": result.error},
            )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "unsupported_media_type", "message": result.error},
        )

    # Pre-generate the recording ID so the storage key and DB row are consistent
    recording_id = uuid.uuid4()
    audio_key = _storage_key(current_user.id, recording_id, file.filename or "audio.bin")

    await storage.upload_file(audio_key, data)

    recording = await svc.create_recording(
        db,
        id=recording_id,
        user_id=current_user.id,
        title=file.filename or "Untitled recording",
        audio_path=audio_key,
        source_type=SourceType.upload,
    )

    pool = await _get_arq_pool()
    await pool.enqueue_job("process_recording", str(recording.id))

    return recording


@router.get("", response_model=list[RecordingListItem])
async def list_recordings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Recording]:
    return await svc.list_recordings(db, user_id=current_user.id)


@router.get("/{recording_id}", response_model=RecordingDetailResponse)
async def get_recording(
    recording_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Recording:
    return await svc.get_recording(db, recording_id=recording_id, user_id=current_user.id)


@router.get("/{recording_id}/status", response_model=RecordingStatusResponse)
async def get_recording_status(
    recording_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Recording:
    return await svc.get_recording_status(db, recording_id=recording_id, user_id=current_user.id)


@router.delete("/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recording(
    recording_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageClient = Depends(get_storage),
) -> None:
    await svc.delete_recording(
        db,
        recording_id=recording_id,
        user_id=current_user.id,
        storage=storage,
    )


@router.post("/{recording_id}/search", response_model=SearchResponse)
@limiter.limit("60/minute")
async def search_recording_endpoint(
    request: Request,
    recording_id: uuid.UUID,
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedder: EmbedderProtocol = Depends(get_embedder),
    vector_store: VectorStoreProtocol = Depends(get_vector_store),
) -> SearchResponse:
    hits, query_time_ms = await search_svc.search_recording(
        db,
        embedder,
        vector_store,
        user_id=current_user.id,
        recording_id=recording_id,
        query=body.query,
        k=body.k,
        speaker_label=body.speaker_label,
    )
    return SearchResponse(
        results=[
            SearchHitResponse(
                segment_id=h.segment_id,
                start_seconds=h.start_seconds,
                end_seconds=h.end_seconds,
                text=h.text,
                score=h.score,
                speaker_label=h.speaker_label,
            )
            for h in hits
        ],
        query_time_ms=query_time_ms,
    )
