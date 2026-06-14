"""create segments table

Revision ID: 003
Revises: 002
Create Date: 2026-06-14 19:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "segments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recording_id", sa.UUID(), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("speaker_label", sa.String(length=100), nullable=True),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["recording_id"], ["recordings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_segments_recording_id", "segments", ["recording_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_segments_recording_id", table_name="segments")
    op.drop_table("segments")
