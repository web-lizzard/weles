"""create outbox envelopes

Revision ID: 3b1a9283e2a9
Revises:
Create Date: 2026-09-13 15:17:26.615290

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3b1a9283e2a9"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    _ = op.create_table(
        "outbox_envelopes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("type_name", sa.String(), nullable=False),
        sa.Column("type_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.String(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'consumed', 'failed')",
            name=op.f("ck_outbox_envelopes_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_envelopes")),
    )
    op.create_index(
        "ix_outbox_envelopes_pending_claim_order",
        "outbox_envelopes",
        ["type_name", "type_version", "created_at"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_outbox_envelopes_pending_claim_order",
        table_name="outbox_envelopes",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_table("outbox_envelopes")
