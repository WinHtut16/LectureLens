"""create recordings table

Revision ID: 002
Revises: 001
Create Date: 2026-06-14 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

sourcetype_enum = sa.Enum("upload", "youtube", name="sourcetype")
recordingstatus_enum = sa.Enum(
    "queued",
    "transcribing",
    "diarizing",
    "embedding",
    "ready",
    "failed",
    name="recordingstatus",
)


def upgrade() -> None:
    sourcetype_enum.create(op.get_bind(), checkfirst=True)
    recordingstatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "recordings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_type", sourcetype_enum, nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("audio_path", sa.String(length=1024), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", recordingstatus_enum, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recordings_user_id", "recordings", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_recordings_user_id", table_name="recordings")
    op.drop_table("recordings")
    recordingstatus_enum.drop(op.get_bind(), checkfirst=True)
    sourcetype_enum.drop(op.get_bind(), checkfirst=True)
