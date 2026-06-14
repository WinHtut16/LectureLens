import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import _DUMMY_HASH, create_access_token, hash_password, verify_password
from app.db.models import User

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "invalid_credentials", "message": "Invalid credentials"},
)


async def signup(email: str, password: str, db: AsyncSession) -> tuple[str, User]:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "email_taken", "message": "Email already registered"},
        )
    user = User(id=uuid.uuid4(), email=email, password_hash=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return create_access_token(str(user.id)), user


async def login(email: str, password: str, db: AsyncSession) -> tuple[str, User]:
    user: User | None = await db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_password(password, _DUMMY_HASH)  # always pay bcrypt cost — prevents timing attack
        raise _INVALID_CREDENTIALS
    if not verify_password(password, user.password_hash):
        raise _INVALID_CREDENTIALS
    return create_access_token(str(user.id)), user
