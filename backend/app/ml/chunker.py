"""Segment chunking — pure list logic, no I/O, no ML.

Merges raw Whisper segments into overlapping windows for embedding.
See ADR-004 for the rationale behind 30s windows / 5s overlap.
"""
from dataclasses import dataclass, field

from app.ml.transcriber import TranscriptSegment


@dataclass
class TranscriptChunk:
    start: float
    end: float
    text: str
    segment_indices: list[int] = field(default_factory=list)


def chunk_segments(
    segments: list[TranscriptSegment],
    window_seconds: int = 30,
    overlap_seconds: int = 5,
) -> list[TranscriptChunk]:
    """Merge *segments* into overlapping windows of ~*window_seconds* each.

    Overlap is achieved by walking backwards from the current window's end to
    find the last segment whose start falls within the overlap zone, making it
    the first segment of the next window.
    """
    if not segments:
        return []

    chunks: list[TranscriptChunk] = []
    i = 0

    while i < len(segments):
        window_start_time = segments[i].start

        # Extend window to include segments whose start < window_start + window_seconds
        j = i
        while (
            j + 1 < len(segments)
            and segments[j + 1].start < window_start_time + window_seconds
        ):
            j += 1

        chunk_segs = segments[i : j + 1]
        chunks.append(
            TranscriptChunk(
                start=chunk_segs[0].start,
                end=chunk_segs[-1].end,
                text=" ".join(s.text for s in chunk_segs),
                segment_indices=list(range(i, j + 1)),
            )
        )

        if j + 1 >= len(segments):
            break  # consumed all segments

        # Find next window start: last segment whose start ≤ (chunk_end - overlap_seconds)
        chunk_end_time = chunk_segs[-1].end
        overlap_boundary = chunk_end_time - overlap_seconds
        next_i = j + 1  # default: no overlap possible
        for k in range(j, i, -1):
            if segments[k].start <= overlap_boundary:
                next_i = k
                break
        i = next_i

    return chunks
