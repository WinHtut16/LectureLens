import uuid
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.core.storage import StorageClient, make_storage_client
from app.db.models import User
from app.db.session import get_db

# auto_error=False: missing Authorization header yields None instead of FastAPI's
# default 403, so we can raise a proper 401 ourselves.
bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_token", "message": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = decode_access_token(credentials.credentials)
        user_id_uuid = uuid.UUID(user_id)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await db.scalar(select(User).where(User.id == user_id_uuid))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@lru_cache(maxsize=1)
def _storage_singleton() -> StorageClient:
    return make_storage_client(settings)


def get_storage() -> StorageClient:
    return _storage_singleton()


import os

from app.ml.embedder import Embedder, EmbedderProtocol
from app.ml.vector_store import VectorStore


@lru_cache(maxsize=1)
def _embedder_singleton() -> EmbedderProtocol:
    return Embedder()


def get_embedder() -> EmbedderProtocol:
    return _embedder_singleton()


@lru_cache(maxsize=1)
def _vector_store_singleton() -> VectorStore:
    vs = VectorStore()
    if os.path.exists(settings.FAISS_INDEX_PATH):
        vs.load(settings.FAISS_INDEX_PATH)
    return vs


def get_vector_store() -> VectorStore:
    return _vector_store_singleton()
