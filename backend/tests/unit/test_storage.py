"""Unit tests for app.core.storage — local backend only."""

import pytest

from app.core.storage import LocalStorageClient


@pytest.fixture
def storage(tmp_path):
    return LocalStorageClient(base_path=str(tmp_path))


async def test_upload_writes_bytes_to_expected_path(storage, tmp_path):
    data = b"audio bytes here"
    returned_key = await storage.upload_file("audio/user1/rec.mp3", data)

    assert returned_key == "audio/user1/rec.mp3"
    dest = tmp_path / "audio" / "user1" / "rec.mp3"
    assert dest.exists()
    assert dest.read_bytes() == data


async def test_upload_creates_intermediate_directories(storage, tmp_path):
    await storage.upload_file("a/b/c/d.wav", b"wav")
    assert (tmp_path / "a" / "b" / "c" / "d.wav").exists()


async def test_delete_removes_file(storage, tmp_path):
    await storage.upload_file("audio/test.mp3", b"data")
    dest = tmp_path / "audio" / "test.mp3"
    assert dest.exists()

    await storage.delete_file("audio/test.mp3")
    assert not dest.exists()


async def test_delete_nonexistent_file_is_noop(storage):
    # Should not raise even if the file never existed
    await storage.delete_file("does/not/exist.mp3")


async def test_download_returns_uploaded_bytes(storage, tmp_path):
    data = b"audio content for download"
    await storage.upload_file("audio/user1/rec.wav", data)

    downloaded = await storage.download_file("audio/user1/rec.wav")
    assert downloaded == data


async def test_download_missing_file_raises(storage):
    with pytest.raises(FileNotFoundError):
        await storage.download_file("does/not/exist.mp3")
