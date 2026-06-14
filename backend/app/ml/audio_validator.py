"""Magic-byte audio validation.

Validates by content (magic bytes via python-magic), not by file extension.
Returns a typed result so callers get structured info without raising.
"""

from dataclasses import dataclass

import magic

# MIME types accepted for upload
_ALLOWED_MIMES: frozenset[str] = frozenset(
    {
        "audio/mpeg",       # mp3
        "audio/wav",        # wav
        "audio/x-wav",      # wav (alternate)
        "audio/mp4",        # m4a
        "audio/x-m4a",      # m4a (alternate)
        "audio/ogg",        # ogg
        "audio/vnd.wave",   # wav (some libmagic versions)
    }
)


@dataclass(frozen=True)
class AudioValidationResult:
    valid: bool
    error: str | None
    detected_mime: str


def validate_audio(data: bytes, max_bytes: int) -> AudioValidationResult:
    """Validate raw audio bytes.

    Args:
        data: raw file bytes (already read from the upload)
        max_bytes: maximum allowed size in bytes

    Returns:
        AudioValidationResult with valid=True on success, or valid=False + error on failure.
    """
    if len(data) > max_bytes:
        return AudioValidationResult(
            valid=False,
            error=f"File exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB",
            detected_mime="",
        )

    detected = magic.from_buffer(data, mime=True)

    if detected not in _ALLOWED_MIMES:
        return AudioValidationResult(
            valid=False,
            error=f"Unsupported file type '{detected}'. Allowed: mp3, wav, m4a, ogg",
            detected_mime=detected,
        )

    return AudioValidationResult(valid=True, error=None, detected_mime=detected)
