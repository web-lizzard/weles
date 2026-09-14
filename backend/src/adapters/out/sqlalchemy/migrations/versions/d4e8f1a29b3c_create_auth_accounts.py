"""create auth_accounts

Revision ID: d4e8f1a29b3c
Revises: c24cb831e287
Create Date: 2026-09-14 02:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e8f1a29b3c"
down_revision: str | Sequence[str] | None = "c24cb831e287"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    _ = op.create_table(
        "auth_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_accounts")),
        sa.UniqueConstraint("email", name=op.f("uq_auth_accounts_email")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("auth_accounts")
