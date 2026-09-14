from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adapters.auth.exceptions import EmailAlreadyRegisteredError
from adapters.auth.model import Account, EmailAddress, PasswordHash
from adapters.auth.sqlalchemy_models import AuthAccountRow
from domain.shared.identity.model import UserId


class SqlAlchemyAccountStore:
    """`AccountStore` on Postgres. Auth has no application layer and no
    `UnitOfWork`: each `save` is one row in its own session and commit."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, account: Account) -> None:
        """A unique-constraint violation on `email` becomes
        `EmailAlreadyRegisteredError`; the store never checks-then-inserts."""
        row = _account_to_row(account)
        async with self._session_factory() as session:
            try:
                _ = await session.merge(row)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise EmailAlreadyRegisteredError from None

    async def by_email(self, email: EmailAddress) -> Account | None:
        async with self._session_factory() as session:
            statement = select(AuthAccountRow).where(
                AuthAccountRow.email == email.value
            )
            row = (await session.execute(statement)).scalar_one_or_none()
            if row is None:
                return None
            return _row_to_account(row)

    async def exists(self, user_id: UserId) -> bool:
        async with self._session_factory() as session:
            statement = select(AuthAccountRow.id).where(
                AuthAccountRow.id == user_id.value
            )
            row_id = (await session.execute(statement)).scalar_one_or_none()
            return row_id is not None


def _account_to_row(account: Account) -> AuthAccountRow:
    return AuthAccountRow(
        id=account.id.value,
        email=account.email.value,
        password_hash=account.password_hash.value,
        created_at=account.created_at,
    )


def _row_to_account(row: AuthAccountRow) -> Account:
    return Account(
        id=UserId(value=row.id),
        email=EmailAddress(value=row.email),
        password_hash=PasswordHash(value=row.password_hash),
        created_at=row.created_at,
    )
