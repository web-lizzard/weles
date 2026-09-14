from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from adapters.out.sqlalchemy.base import Base


class AuthAttemptRow(Base):
    """One counted attempt of one action from one source, at a point in time.
    `AttemptLedger.record` inserts a row; `ensure_allowed` counts and reads the
    oldest row within the window for a given `(action, source)`."""

    __tablename__: str = "auth_attempts"
    __table_args__: tuple[Index] = (
        Index(
            "ix_auth_attempts_action_source_attempted_at",
            "action",
            "source",
            "attempted_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AuthAccountRow(Base):
    """`email` holds `EmailAddress.value`, already canonical, so the unique
    constraint is the uniqueness guarantee two concurrent registrations race
    against."""

    __tablename__: str = "auth_accounts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
