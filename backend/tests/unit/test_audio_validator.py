"""Unit tests for app.ml.audio_validator."""

import struct

import pytest

from app.ml.audio_validator import validate_audio

_MAX = 50 * 1024 * 1024  # 50 MB


def _mp3_magic() -> bytes:
    # Minimal MPEG1 Layer3 frame: sync word + header + zero-padded frame body
    # 0xFF 0xFB = sync (11 bits) + MPEG1 + Layer3 + no CRC
    # 0x90 = 128 kbps index + 44100 Hz index
    # 0x00 = joint stereo + no padding
    return b"\xff\xfb\x90\x00" + b"\x00" * 413  # one 417-byte MP3 frame


def _wav_magic() -> bytes:
    # Minimal valid WAV (PCM mono 44100 Hz 16-bit, ~1 sample of silence)
    data = b"\x00" * 2
    fmt_size = 16
    num_ch, rate, bits = 1, 44100, 16
    block_align = num_ch * bits // 8
    byte_rate = rate * block_align
    riff_size = 4 + (8 + fmt_size) + (8 + len(data))
    return (
        b"RIFF"
        + struct.pack("<I", riff_size)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<I", fmt_size)
        + struct.pack("<H", 1)  # PCM
        + struct.pack("<HI", num_ch, rate)
        + struct.pack("<IHH", byte_rate, block_align, bits)
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )


def _fake_mp3_magic() -> bytes:
    # Plain text content with .mp3 extension — should be rejected
    return b"Hello, this is definitely not an mp3 file." + b" " * 60


def test_valid_mp3():
    result = validate_audio(_mp3_magic(), max_bytes=_MAX)
    assert result.valid is True
    assert result.error is None
    assert "mpeg" in result.detected_mime or "mp3" in result.detected_mime


def test_valid_wav():
    result = validate_audio(_wav_magic(), max_bytes=_MAX)
    assert result.valid is True
    assert result.error is None
    assert "wav" in result.detected_mime or "wave" in result.detected_mime.lower()


def test_fake_mp3_wrong_magic_bytes():
    """A text file renamed to .mp3 must be rejected by content, not extension."""
    result = validate_audio(_fake_mp3_magic(), max_bytes=_MAX)
    assert result.valid is False
    assert result.error is not None
    assert "Unsupported" in result.error


def test_oversized_file_rejected():
    limit = 1024  # 1 KB for this test
    data = b"\x00" * (limit + 1)
    result = validate_audio(data, max_bytes=limit)
    assert result.valid is False
    assert result.error is not None
    assert "exceeds maximum" in result.error
    assert result.detected_mime == ""
