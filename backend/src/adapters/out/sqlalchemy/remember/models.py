from datetime import datetime

from adapters.out.sqlalchemy.base import Base
from adapters.out.sqlalchemy.remember.types import (
    CardIdType,
    OpaqueSchedulerStateType,
    ResumeHorizonType,
    ShowingLimitType,
    SittingIdType,
)
from adapters.out.sqlalchemy.shared.types import StrEnumType
from domain.remember.value_objects import (
    CardId,
    Grade,
    OpaqueSchedulerState,
    ResumeHorizon,
    SchedulerAlgorithm,
    ShowingLimit,
    SittingId,
)
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

_REVIEW_EVENT_KIND_SQL = "('graded', 'rejected', 'revealed')"
_GRADE_SQL = "(" + ", ".join(f"'{grade.value}'" for grade in Grade) + ")"
_SCHEDULER_ALGORITHM_SQL = (
    "(" + ", ".join(f"'{algorithm.value}'" for algorithm in SchedulerAlgorithm) + ")"
)


class RememberSittingRow(Base):
    __tablename__: str = "remember_sittings"
    __table_args__: tuple[CheckConstraint, CheckConstraint] = (
        CheckConstraint("showing_limit >= 1", name="showing_limit_positive"),
        CheckConstraint(
            "resume_horizon > interval '0'",
            name="resume_horizon_positive",
        ),
    )

    id: Mapped[SittingId] = mapped_column(SittingIdType, primary_key=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    showing_limit: Mapped[ShowingLimit] = mapped_column(
        ShowingLimitType, nullable=False
    )
    resume_horizon: Mapped[ResumeHorizon] = mapped_column(
        ResumeHorizonType, nullable=False
    )

    cards: Mapped[list["RememberSittingCardRow"]] = relationship(
        "RememberSittingCardRow",
        cascade="all, delete-orphan",
    )


class RememberSittingCardRow(Base):
    __tablename__: str = "remember_sitting_cards"
    __table_args__: tuple[PrimaryKeyConstraint] = (
        PrimaryKeyConstraint("sitting_id", "card_id"),
    )

    sitting_id: Mapped[SittingId] = mapped_column(
        SittingIdType,
        ForeignKey("remember_sittings.id", ondelete="CASCADE"),
        nullable=False,
    )
    card_id: Mapped[CardId] = mapped_column(CardIdType, nullable=False)


class RememberReviewEventRow(Base):
    __tablename__: str = "remember_review_events"
    __table_args__: tuple[
        CheckConstraint, CheckConstraint, CheckConstraint, Index, Index
    ] = (
        CheckConstraint(
            f"kind IN {_REVIEW_EVENT_KIND_SQL}",
            name="kind_valid",
        ),
        CheckConstraint(
            f"grade IN {_GRADE_SQL}",
            name="grade_valid",
        ),
        CheckConstraint(
            "(kind = 'graded') = (grade IS NOT NULL)",
            name="grade_iff_graded",
        ),
        Index(
            "ix_remember_review_events_card_id_reviewed_at",
            "card_id",
            "reviewed_at",
        ),
        Index(
            "ix_remember_review_events_sitting_id_reviewed_at",
            "sitting_id",
            "reviewed_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sitting_id: Mapped[SittingId] = mapped_column(
        SittingIdType,
        ForeignKey("remember_sittings.id"),
        nullable=False,
    )
    card_id: Mapped[CardId] = mapped_column(CardIdType, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    grade: Mapped[str | None] = mapped_column(String, nullable=True)


class RememberSchedulingStateRow(Base):
    __tablename__: str = "remember_scheduling_states"
    __table_args__: tuple[CheckConstraint] = (
        CheckConstraint(
            f"stamp_algorithm IN {_SCHEDULER_ALGORITHM_SQL}",
            name="stamp_algorithm_valid",
        ),
    )

    card_id: Mapped[CardId] = mapped_column(CardIdType, primary_key=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduler_state: Mapped[OpaqueSchedulerState] = mapped_column(
        OpaqueSchedulerStateType, nullable=False
    )
    stamp_algorithm: Mapped[SchedulerAlgorithm] = mapped_column(
        StrEnumType(SchedulerAlgorithm), nullable=False
    )
    stamp_parameter_version: Mapped[str] = mapped_column(String, nullable=False)
