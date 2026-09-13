from datetime import datetime

from adapters.out.sqlalchemy.base import Base
from adapters.out.sqlalchemy.capture.types import (
    ConversationRequestType,
    CoverageHistoryType,
    DraftingConsentType,
    LabelType,
    MessageContentType,
    MessageIdType,
    NoteContentType,
    NoteIdType,
    SessionIdType,
    SessionTopicType,
    TagIdType,
    TopicIdType,
    VectorType,
)
from adapters.out.sqlalchemy.shared.types import StrEnumType
from domain.capture.value_objects import (
    CapturePhase,
    ConversationRequest,
    Coverage,
    DraftingConsent,
    Label,
    MessageContent,
    MessageId,
    MessageRole,
    NoteContent,
    NoteId,
    NoteStatus,
    SessionId,
    SessionStatus,
    SessionTopic,
    TagId,
    TopicId,
)
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

_SESSION_STATUS_VALUES = tuple(status.value for status in SessionStatus)
_CAPTURE_PHASE_VALUES = tuple(phase.value for phase in CapturePhase)
_MESSAGE_ROLE_VALUES = tuple(role.value for role in MessageRole)
_NOTE_STATUS_VALUES = tuple(status.value for status in NoteStatus)


class CaptureSessionRow(Base):
    __tablename__: str = "capture_sessions"
    __table_args__: tuple[CheckConstraint, CheckConstraint] = (
        CheckConstraint(f"status IN {_SESSION_STATUS_VALUES}", name="status_valid"),
        CheckConstraint(f"phase IN {_CAPTURE_PHASE_VALUES}", name="phase_valid"),
    )

    id: Mapped[SessionId] = mapped_column(SessionIdType, primary_key=True)
    topic: Mapped[SessionTopic | None] = mapped_column(SessionTopicType, nullable=True)
    note_id: Mapped[NoteId | None] = mapped_column(NoteIdType, nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        StrEnumType(SessionStatus), nullable=False
    )
    phase: Mapped[CapturePhase] = mapped_column(
        StrEnumType(CapturePhase), nullable=False
    )
    drafting_consent: Mapped[DraftingConsent | None] = mapped_column(
        DraftingConsentType, nullable=False
    )
    conversation_request: Mapped[ConversationRequest | None] = mapped_column(
        ConversationRequestType, nullable=False
    )
    assessments: Mapped[tuple[Coverage, ...]] = mapped_column(
        CoverageHistoryType, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)


class CaptureMessageRow(Base):
    __tablename__: str = "capture_messages"
    __table_args__: tuple[CheckConstraint, UniqueConstraint, Index] = (
        CheckConstraint(f"role IN {_MESSAGE_ROLE_VALUES}", name="role_valid"),
        UniqueConstraint("position"),
        Index("ix_capture_messages_session_id_position", "session_id", "position"),
    )

    id: Mapped[MessageId] = mapped_column(MessageIdType, primary_key=True)
    position: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    session_id: Mapped[SessionId] = mapped_column(
        SessionIdType, ForeignKey("capture_sessions.id"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(StrEnumType(MessageRole), nullable=False)
    content: Mapped[MessageContent] = mapped_column(MessageContentType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CaptureTopicRow(Base):
    __tablename__: str = "capture_topics"

    id: Mapped[TopicId] = mapped_column(TopicIdType, primary_key=True)
    label: Mapped[Label] = mapped_column(LabelType, nullable=False)
    embedding_values: Mapped[tuple[float, ...]] = mapped_column(
        VectorType, nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CaptureTagRow(Base):
    __tablename__: str = "capture_tags"

    id: Mapped[TagId] = mapped_column(TagIdType, primary_key=True)
    label: Mapped[Label] = mapped_column(LabelType, nullable=False)
    embedding_values: Mapped[tuple[float, ...]] = mapped_column(
        VectorType, nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CaptureNoteRow(Base):
    __tablename__: str = "capture_notes"
    __table_args__: tuple[CheckConstraint] = (
        CheckConstraint(f"status IN {_NOTE_STATUS_VALUES}", name="status_valid"),
    )

    id: Mapped[NoteId] = mapped_column(NoteIdType, primary_key=True)
    session_id: Mapped[SessionId] = mapped_column(
        SessionIdType, ForeignKey("capture_sessions.id"), nullable=False
    )
    topic_id: Mapped[TopicId] = mapped_column(
        TopicIdType, ForeignKey("capture_topics.id"), nullable=False
    )
    content: Mapped[NoteContent] = mapped_column(NoteContentType, nullable=False)
    status: Mapped[NoteStatus] = mapped_column(StrEnumType(NoteStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tags: Mapped[list["CaptureNoteTagRow"]] = relationship(
        "CaptureNoteTagRow",
        order_by="CaptureNoteTagRow.position",
        cascade="all, delete-orphan",
    )


class CaptureNoteTagRow(Base):
    __tablename__: str = "capture_note_tags"
    __table_args__: tuple[PrimaryKeyConstraint] = (
        PrimaryKeyConstraint("note_id", "position"),
    )

    note_id: Mapped[NoteId] = mapped_column(
        NoteIdType,
        ForeignKey("capture_notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    tag_id: Mapped[TagId] = mapped_column(
        TagIdType, ForeignKey("capture_tags.id"), nullable=False
    )
