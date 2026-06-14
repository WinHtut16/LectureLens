import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class SourceType(str, enum.Enum):
    upload = "upload"
    youtube = "youtube"


class RecordingStatus(str, enum.Enum):
    queued = "queued"
    transcribing = "transcribing"
    diarizing = "diarizing"
    embedding = "embedding"
    ready = "ready"
    failed = "failed"


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="sourcetype"), nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    audio_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus, name="recordingstatus"),
        nullable=False,
        default=RecordingStatus.queued,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
