"""Unit tests for chunk_segments — no mocks needed; this is pure list logic."""

import pytest

from app.ml.chunker import TranscriptChunk, chunk_segments
from app.ml.transcriber import TranscriptSegment


def _seg(start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


def test_short_segments_fit_in_one_chunk():
    segs = [_seg(0, 5, "alpha"), _seg(5, 10, "beta"), _seg(10, 15, "gamma")]
    chunks = chunk_segments(segs, window_seconds=30, overlap_seconds=5)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.start == 0.0
    assert chunk.end == 15.0
    assert "alpha" in chunk.text
    assert "gamma" in chunk.text
    assert chunk.segment_indices == [0, 1, 2]


def test_empty_segments_returns_empty_list():
    assert chunk_segments([], window_seconds=30, overlap_seconds=5) == []


def test_single_long_segment_returns_one_chunk():
    segs = [_seg(0, 90, "long monologue")]
    chunks = chunk_segments(segs, window_seconds=30, overlap_seconds=5)
    assert len(chunks) == 1
    assert chunks[0].start == 0.0
    assert chunks[0].end == 90.0
    assert chunks[0].text == "long monologue"


def test_90s_audio_produces_multiple_chunks_with_overlap():
    # 18 segments of 5 s each → 0-5, 5-10, …, 85-90
    segs = [_seg(float(i * 5), float(i * 5 + 5), f"word{i}") for i in range(18)]
    chunks = chunk_segments(segs, window_seconds=30, overlap_seconds=5)

    # With 5s segments, window=30, overlap=5 → 4 chunks
    assert len(chunks) == 4

    # Start / end integrity: each chunk's start matches its first segment's start
    for chunk in chunks:
        first_idx = chunk.segment_indices[0]
        last_idx = chunk.segment_indices[-1]
        assert chunk.start == segs[first_idx].start
        assert chunk.end == segs[last_idx].end

    # Overlap: consecutive chunks share at least one segment index
    for k in range(len(chunks) - 1):
        shared = set(chunks[k].segment_indices) & set(chunks[k + 1].segment_indices)
        assert len(shared) > 0, f"chunks {k} and {k+1} share no segments"
        # The shared segment text appears in both chunks' text
        for idx in shared:
            assert segs[idx].text in chunks[k].text
            assert segs[idx].text in chunks[k + 1].text


def test_chunk_boundaries_match_contained_segments():
    # Irregular segment lengths (closer to real Whisper output)
    segs = [
        _seg(0.0, 3.2, "hello"),
        _seg(3.2, 7.8, "world"),
        _seg(7.8, 14.1, "foo"),
        _seg(14.1, 22.0, "bar"),
        _seg(22.0, 30.5, "baz"),
        _seg(30.5, 38.0, "qux"),
        _seg(38.0, 45.0, "end"),
    ]
    chunks = chunk_segments(segs, window_seconds=30, overlap_seconds=5)

    for chunk in chunks:
        first = segs[chunk.segment_indices[0]]
        last = segs[chunk.segment_indices[-1]]
        assert chunk.start == first.start
        assert chunk.end == last.end
        # All segment texts must appear in the chunk text
        for idx in chunk.segment_indices:
            assert segs[idx].text in chunk.text
