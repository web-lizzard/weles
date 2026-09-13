"""create capture tables

Revision ID: 2ce37af2f0f8
Revises: 3b1a9283e2a9
Create Date: 2026-09-13 17:20:03.757986

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from adapters.out.sqlalchemy.capture.types import VectorType

# revision identifiers, used by Alembic.
revision: str = "2ce37af2f0f8"
down_revision: str | Sequence[str] | None = "3b1a9283e2a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    _ = op.create_table(
        "capture_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("note_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("drafting_consent", sa.Boolean(), nullable=False),
        sa.Column("conversation_request", sa.Boolean(), nullable=False),
        sa.Column("assessments", sa.ARRAY(sa.Double[float]()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "phase IN ('conversing', 'drafting')",
            name=op.f("ck_capture_sessions_phase_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('open', 'closed')",
            name=op.f("ck_capture_sessions_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capture_sessions")),
    )
    _ = op.create_table(
        "capture_tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("embedding_values", VectorType(), nullable=False),
        sa.Column("embedding_model", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capture_tags")),
    )
    _ = op.create_table(
        "capture_topics",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("embedding_values", VectorType(), nullable=False),
        sa.Column("embedding_model", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capture_topics")),
    )
    _ = op.create_table(
        "capture_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "position", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('user', 'agent')", name=op.f("ck_capture_messages_role_valid")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["capture_sessions.id"],
            name=op.f("fk_capture_messages_session_id_capture_sessions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capture_messages")),
        sa.UniqueConstraint("position", name=op.f("uq_capture_messages_position")),
    )
    op.create_index(
        "ix_capture_messages_session_id_position",
        "capture_messages",
        ["session_id", "position"],
        unique=False,
    )
    _ = op.create_table(
        "capture_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("topic_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'discarded')",
            name=op.f("ck_capture_notes_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["capture_sessions.id"],
            name=op.f("fk_capture_notes_session_id_capture_sessions"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["capture_topics.id"],
            name=op.f("fk_capture_notes_topic_id_capture_topics"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capture_notes")),
    )
    _ = op.create_table(
        "capture_note_tags",
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["capture_notes.id"],
            name=op.f("fk_capture_note_tags_note_id_capture_notes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["capture_tags.id"],
            name=op.f("fk_capture_note_tags_tag_id_capture_tags"),
        ),
        sa.PrimaryKeyConstraint(
            "note_id", "position", name=op.f("pk_capture_note_tags")
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("capture_note_tags")
    op.drop_table("capture_notes")
    op.drop_index(
        "ix_capture_messages_session_id_position", table_name="capture_messages"
    )
    op.drop_table("capture_messages")
    op.drop_table("capture_topics")
    op.drop_table("capture_tags")
    op.drop_table("capture_sessions")
    op.execute("DROP EXTENSION IF EXISTS vector")
