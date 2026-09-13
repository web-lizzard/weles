"""create distill tables

Revision ID: 85ec052c2b79
Revises: 2ce37af2f0f8
Create Date: 2026-09-13 19:30:20.496370

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "85ec052c2b79"
down_revision: str | Sequence[str] | None = "2ce37af2f0f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    _ = op.create_table(
        "distill_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("topic_id", sa.UUID(), nullable=False),
        sa.Column("topic_label", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("distillation_status", sa.String(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "distillation_status IN ('generating', 'ready', 'failed')",
            name=op.f("ck_distill_notes_distillation_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_distill_notes")),
    )
    _ = op.create_table(
        "distill_cards",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("front", sa.Text(), nullable=False),
        sa.Column("back", sa.Text(), nullable=False),
        sa.Column("anchor_quote", sa.Text(), nullable=False),
        sa.Column("discard_reason", sa.String(), nullable=True),
        sa.Column("discard_detail", sa.Text(), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "discard_reason IN ('ungrounded', 'oversized', 'user_audit', "
            + "'low_quality', 'duplicate')",
            name=op.f("ck_distill_cards_discard_reason_valid"),
        ),
        sa.CheckConstraint(
            "(discard_reason IS NULL) = (discarded_at IS NULL)",
            name=op.f("ck_distill_cards_discard_complete"),
        ),
        sa.CheckConstraint(
            "discard_reason IS NOT NULL OR discard_detail IS NULL",
            name=op.f("ck_distill_cards_discard_detail_needs_reason"),
        ),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["distill_notes.id"],
            name=op.f("fk_distill_cards_note_id_distill_notes"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_distill_cards")),
    )
    op.create_index(
        "ix_distill_cards_note_id_created_at",
        "distill_cards",
        ["note_id", "created_at"],
        unique=False,
    )
    _ = op.create_table(
        "distill_note_tags",
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["distill_notes.id"],
            name=op.f("fk_distill_note_tags_note_id_distill_notes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "note_id", "position", name=op.f("pk_distill_note_tags")
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("distill_cards")
    op.drop_table("distill_note_tags")
    op.drop_table("distill_notes")
