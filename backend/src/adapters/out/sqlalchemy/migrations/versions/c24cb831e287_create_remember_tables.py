"""create remember tables

Revision ID: c24cb831e287
Revises: 85ec052c2b79
Create Date: 2026-09-13 20:46:14.548165

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c24cb831e287"
down_revision: str | Sequence[str] | None = "85ec052c2b79"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    _ = op.create_table(
        "remember_scheduling_states",
        sa.Column("card_id", sa.UUID(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "scheduler_state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("stamp_algorithm", sa.String(), nullable=False),
        sa.Column("stamp_parameter_version", sa.String(), nullable=False),
        sa.CheckConstraint(
            "stamp_algorithm IN ('fsrs')",
            name=op.f("ck_remember_scheduling_states_stamp_algorithm_valid"),
        ),
        sa.PrimaryKeyConstraint("card_id", name=op.f("pk_remember_scheduling_states")),
    )
    _ = op.create_table(
        "remember_sittings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("showing_limit", sa.Integer(), nullable=False),
        sa.Column("resume_horizon", sa.Interval(), nullable=False),
        sa.CheckConstraint(
            "resume_horizon > interval '0'",
            name=op.f("ck_remember_sittings_resume_horizon_positive"),
        ),
        sa.CheckConstraint(
            "showing_limit >= 1",
            name=op.f("ck_remember_sittings_showing_limit_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_remember_sittings")),
    )
    op.create_index(
        op.f("ix_remember_sittings_opened_at"),
        "remember_sittings",
        ["opened_at"],
        unique=False,
    )
    _ = op.create_table(
        "remember_review_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("sitting_id", sa.UUID(), nullable=False),
        sa.Column("card_id", sa.UUID(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("grade", sa.String(), nullable=True),
        sa.CheckConstraint(
            "(kind = 'graded') = (grade IS NOT NULL)",
            name=op.f("ck_remember_review_events_grade_iff_graded"),
        ),
        sa.CheckConstraint(
            "grade IN ('forgot', 'hard', 'good', 'easy')",
            name=op.f("ck_remember_review_events_grade_valid"),
        ),
        sa.CheckConstraint(
            "kind IN ('graded', 'rejected', 'revealed')",
            name=op.f("ck_remember_review_events_kind_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["sitting_id"],
            ["remember_sittings.id"],
            name=op.f("fk_remember_review_events_sitting_id_remember_sittings"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_remember_review_events")),
    )
    op.create_index(
        "ix_remember_review_events_card_id_reviewed_at",
        "remember_review_events",
        ["card_id", "reviewed_at"],
        unique=False,
    )
    op.create_index(
        "ix_remember_review_events_sitting_id_reviewed_at",
        "remember_review_events",
        ["sitting_id", "reviewed_at"],
        unique=False,
    )
    _ = op.create_table(
        "remember_sitting_cards",
        sa.Column("sitting_id", sa.UUID(), nullable=False),
        sa.Column("card_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sitting_id"],
            ["remember_sittings.id"],
            name=op.f("fk_remember_sitting_cards_sitting_id_remember_sittings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "sitting_id", "card_id", name=op.f("pk_remember_sitting_cards")
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("remember_review_events")
    op.drop_table("remember_sitting_cards")
    op.drop_table("remember_scheduling_states")
    op.drop_table("remember_sittings")
