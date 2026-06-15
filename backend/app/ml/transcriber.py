"""Transcription interface and implementations.

WhisperModel is imported lazily inside FasterWhisperTranscriber.__init__ so this
module is safe to import in unit tests without triggering a model download.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


@runtime_checkable
class TranscriberProtocol(Protocol):
    def transcribe(self, audio_path: str) -> list[TranscriptSegment]: ...


class FasterWhisperTranscriber:
    def __init__(self, model_size: str = "base") -> None:
        # Lazy import: WhisperModel is heavy; importing at module level would
        # make every unit-test file trigger a model download.
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]  # no stubs available

        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_path: str) -> list[TranscriptSegment]:
        segments, _ = self._model.transcribe(audio_path)
        return [TranscriptSegment(start=s.start, end=s.end, text=s.text.strip()) for s in segments]


class MockTranscriber:
    """Drop-in for tests: returns a fixed list of segments without loading any model."""

    def __init__(self, segments: list[TranscriptSegment] | None = None) -> None:
        self._segments = segments or []

    def transcribe(self, audio_path: str) -> list[TranscriptSegment]:
        return self._segments
