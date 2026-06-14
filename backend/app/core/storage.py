"""Object storage abstraction.

Two backends:
  local — writes to LOCAL_STORAGE_PATH on disk (dev / CI)
  s3    — S3-compatible (Supabase Storage, Cloudflare R2) via boto3 in a thread
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.core.config import Settings


class StorageClient(ABC):
    @abstractmethod
    async def upload_file(self, key: str, data: bytes) -> str:
        """Upload data at *key* and return the key."""

    @abstractmethod
    async def download_file(self, key: str) -> bytes:
        """Download the object at *key* and return its bytes. Raises FileNotFoundError if missing."""

    @abstractmethod
    async def delete_file(self, key: str) -> None:
        """Delete the object at *key*. No-op if it does not exist."""


class LocalStorageClient(StorageClient):
    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)

    async def upload_file(self, key: str, data: bytes) -> str:
        dest = self._base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return key

    async def download_file(self, key: str) -> bytes:
        target = self._base / key
        if not target.exists():
            raise FileNotFoundError(f"Storage key not found: {key}")
        return target.read_bytes()

    async def delete_file(self, key: str) -> None:
        target = self._base / key
        if target.exists():
            target.unlink()


class S3StorageClient(StorageClient):
    def __init__(self, bucket: str, endpoint_url: str, access_key: str, secret_key: str) -> None:
        self._bucket = bucket
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key

    def _make_client(self) -> Any:
        import boto3  # type: ignore[import-untyped]  # no stubs available

        return boto3.client(
            "s3",
            endpoint_url=self._endpoint_url or None,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )

    async def upload_file(self, key: str, data: bytes) -> str:
        client = self._make_client()
        await asyncio.to_thread(client.put_object, Bucket=self._bucket, Key=key, Body=data)
        return key

    async def download_file(self, key: str) -> bytes:
        client = self._make_client()

        def _get() -> bytes:
            response = client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()  # type: ignore[no-any-return]

        return await asyncio.to_thread(_get)

    async def delete_file(self, key: str) -> None:
        client = self._make_client()
        await asyncio.to_thread(client.delete_object, Bucket=self._bucket, Key=key)


def make_storage_client(cfg: Settings) -> StorageClient:
    if cfg.STORAGE_BACKEND == "s3":
        return S3StorageClient(
            bucket=cfg.S3_BUCKET,
            endpoint_url=cfg.S3_ENDPOINT,
            access_key=cfg.S3_ACCESS_KEY,
            secret_key=cfg.S3_SECRET_KEY,
        )
    return LocalStorageClient(base_path=cfg.LOCAL_STORAGE_PATH)
