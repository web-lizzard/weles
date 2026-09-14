"""add owner to capture tables

Revision ID: d52a781c5827
Revises: d4e8f1a29b3c
Create Date: 2026-09-14 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d52a781c5827"
down_revision: str | Sequence[str] | None = "d4e8f1a29b3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("capture_sessions", sa.Column("owner_id", sa.UUID(), nullable=False))
    op.add_column("capture_notes", sa.Column("owner_id", sa.UUID(), nullable=False))
    op.add_column("capture_topics", sa.Column("owner_id", sa.UUID(), nullable=False))
    op.add_column("capture_tags", sa.Column("owner_id", sa.UUID(), nullable=False))
    op.create_index(op.f("ix_capture_topics_owner_id"), "capture_topics", ["owner_id"])
    op.create_index(op.f("ix_capture_tags_owner_id"), "capture_tags", ["owner_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_capture_tags_owner_id"), table_name="capture_tags")
    op.drop_index(op.f("ix_capture_topics_owner_id"), table_name="capture_topics")
    op.drop_column("capture_tags", "owner_id")
    op.drop_column("capture_topics", "owner_id")
    op.drop_column("capture_notes", "owner_id")
    op.drop_column("capture_sessions", "owner_id")
