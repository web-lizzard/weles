"""add owner to remember sittings

Revision ID: 79c5a626506c
Revises: e63f914a8d6b
Create Date: 2026-09-14 05:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "79c5a626506c"
down_revision: str | Sequence[str] | None = "e63f914a8d6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("remember_sittings", sa.Column("owner_id", sa.UUID(), nullable=False))
    op.create_index(
        op.f("ix_remember_sittings_owner_id_opened_at"),
        "remember_sittings",
        ["owner_id", "opened_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_remember_sittings_owner_id_opened_at"),
        table_name="remember_sittings",
    )
    op.drop_column("remember_sittings", "owner_id")
