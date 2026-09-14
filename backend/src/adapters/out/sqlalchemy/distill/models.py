from datetime import datetime
from uuid import UUID

from adapters.out.sqlalchemy.base import Base
from adapters.out.sqlalchemy.distill.types import (
    AnchorType,
    CardIdType,
    CardSideType,
    NoteContentType,
    NoteIdType,
    SessionIdType,
)
from adapters.out.sqlalchemy.shared.types import StrEnumType
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    DiscardReason,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
)
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

_DISTILLATION_STATUS_VALUES = tuple(status.value for status in DistillationStatus)
_DISCARD_REASON_VALUES = tuple(reason.value for reason in DiscardReason)


class DistillNoteRow(Base):
    __tablename__: str = "distill_notes"
    __table_args__: tuple[CheckConstraint] = (
        CheckConstraint(
            f"distillation_status IN {_DISTILLATION_STATUS_VALUES}",
            name="distillation_status_valid",
        ),
    )

    id: Mapped[NoteId] = mapped_column(NoteIdType, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    session_id: Mapped[SessionId] = mapped_column(SessionIdType, nullable=False)
    topic_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    topic_label: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[NoteContent] = mapped_column(NoteContentType, nullable=False)
    distillation_status: Mapped[DistillationStatus] = mapped_column(
        StrEnumType(DistillationStatus), nullable=False
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    tags: Mapped[list["DistillNoteTagRow"]] = relationship(
        "DistillNoteTagRow",
        order_by="DistillNoteTagRow.position",
        cascade="all, delete-orphan",
    )


class DistillNoteTagRow(Base):
    __tablename__: str = "distill_note_tags"
    __table_args__: tuple[PrimaryKeyConstraint] = (
        PrimaryKeyConstraint("note_id", "position"),
    )

    note_id: Mapped[NoteId] = mapped_column(
        NoteIdType,
        ForeignKey("distill_notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    tag_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)


class DistillCardRow(Base):
    __tablename__: str = "distill_cards"
    __table_args__: tuple[CheckConstraint, CheckConstraint, CheckConstraint, Index] = (
        CheckConstraint(
            f"discard_reason IN {_DISCARD_REASON_VALUES}",
            name="discard_reason_valid",
        ),
        CheckConstraint(
            "(discard_reason IS NULL) = (discarded_at IS NULL)",
            name="discard_complete",
        ),
        CheckConstraint(
            "discard_reason IS NOT NULL OR discard_detail IS NULL",
            name="discard_detail_needs_reason",
        ),
        Index("ix_distill_cards_note_id_created_at", "note_id", "created_at"),
    )

    id: Mapped[CardId] = mapped_column(CardIdType, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    note_id: Mapped[NoteId] = mapped_column(
        NoteIdType, ForeignKey("distill_notes.id"), nullable=False
    )
    front: Mapped[CardSide] = mapped_column(CardSideType, nullable=False)
    back: Mapped[CardSide] = mapped_column(CardSideType, nullable=False)
    anchor_quote: Mapped[Anchor] = mapped_column(AnchorType, nullable=False)
    discard_reason: Mapped[DiscardReason | None] = mapped_column(
        StrEnumType(DiscardReason), nullable=True
    )
    discard_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    discarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
