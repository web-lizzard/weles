from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from adapters.out.sqlalchemy.base import Base


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
