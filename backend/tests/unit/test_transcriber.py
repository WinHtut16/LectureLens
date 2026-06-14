"""Unit tests for the transcriber interface.

FasterWhisperTranscriber is never instantiated here — doing so would trigger
a model download. We verify the contract through MockTranscriber only.
"""
import pytest

from app.ml.transcriber import MockTranscriber, TranscriptSegment, TranscriberProtocol


def _make_segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start=0.0, end=5.0, text="hello"),
        TranscriptSegment(start=5.0, end=10.0, text="world"),
        TranscriptSegment(start=10.0, end=15.5, text="goodbye"),
    ]


def test_mock_transcriber_returns_injected_segments():
    segs = _make_segments()
    transcriber = MockTranscriber(segments=segs)
    result = transcriber.transcribe("/fake/path.wav")
    assert result == segs


def test_mock_transcriber_default_returns_empty_list():
    transcriber = MockTranscriber()
    result = transcriber.transcribe("/fake/path.wav")
    assert result == []


def test_mock_transcriber_satisfies_protocol():
    transcriber = MockTranscriber(segments=_make_segments())
    assert isinstance(transcriber, TranscriberProtocol)


def test_transcript_segment_fields_are_accessible():
    seg = TranscriptSegment(start=1.5, end=4.2, text="test segment")
    assert seg.start == 1.5
    assert seg.end == 4.2
    assert seg.text == "test segment"


def test_transcript_segment_is_frozen():
    """TranscriptSegment must be immutable — frozen dataclass."""
    seg = TranscriptSegment(start=0.0, end=1.0, text="x")
    with pytest.raises((AttributeError, TypeError)):
        seg.start = 99.0  # type: ignore[misc]


def test_mock_transcriber_ignores_audio_path():
    """Path argument is accepted but irrelevant for the mock."""
    segs = _make_segments()
    t = MockTranscriber(segments=segs)
    assert t.transcribe("anything.mp3") == segs
    assert t.transcribe("anything_else.wav") == segs
