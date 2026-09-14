"""add owner to distill tables

Revision ID: e63f914a8d6b
Revises: d52a781c5827
Create Date: 2026-09-14 04:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e63f914a8d6b"
down_revision: str | Sequence[str] | None = "d52a781c5827"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("distill_notes", sa.Column("owner_id", sa.UUID(), nullable=False))
    op.add_column("distill_cards", sa.Column("owner_id", sa.UUID(), nullable=False))
    op.create_index(op.f("ix_distill_notes_owner_id"), "distill_notes", ["owner_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_distill_notes_owner_id"), table_name="distill_notes")
    op.drop_column("distill_cards", "owner_id")
    op.drop_column("distill_notes", "owner_id")
