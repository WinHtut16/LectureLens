"""Semantic search over a recording's indexed segments."""

import asyncio
import time
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Recording, RecordingStatus, Segment
from app.ml.embedder import EmbedderProtocol
from app.ml.vector_store import VectorStoreProtocol


@dataclass(frozen=True)
class SearchHit:
    segment_id: str
    start_seconds: float
    end_seconds: float
    text: str
    score: float
    speaker_label: str | None


async def search_recording(
    db: AsyncSession,
    embedder: EmbedderProtocol,
    vector_store: VectorStoreProtocol,
    *,
    user_id: uuid.UUID,
    recording_id: uuid.UUID,
    query: str,
    k: int = 10,
    speaker_label: str | None = None,
) -> tuple[list[SearchHit], float]:
    """Semantic search; returns (hits, query_time_ms).

    Raises:
        HTTPException 404 — recording not found.
        HTTPException 403 — recording belongs to a different user.
        HTTPException 400 — recording status is not 'ready'.
    """
    recording = await db.scalar(select(Recording).where(Recording.id == recording_id))
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Recording not found"},
        )
    if recording.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Access denied"},
        )
    if recording.status != RecordingStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "not_indexed", "message": "Recording is not yet indexed"},
        )

    t0 = time.monotonic()

    query_vector = await asyncio.to_thread(embedder.embed_one, query)
    results = vector_store.search(
        query_vector=query_vector,
        recording_ids=[str(recording_id)],
        k=k,
        speaker_label=speaker_label,
    )

    if not results:
        return [], (time.monotonic() - t0) * 1000

    seg_ids = [uuid.UUID(r.segment_id) for r in results]
    rows = await db.scalars(select(Segment).where(Segment.id.in_(seg_ids)))
    seg_map = {str(s.id): s for s in rows}

    hits: list[SearchHit] = []
    for r in results:
        seg = seg_map.get(r.segment_id)
        if seg is None:
            continue
        hits.append(
            SearchHit(
                segment_id=r.segment_id,
                start_seconds=r.start_seconds,
                end_seconds=seg.end_seconds,
                text=seg.text,
                score=r.score,
                speaker_label=r.speaker_label,
            )
        )

    return hits, (time.monotonic() - t0) * 1000
