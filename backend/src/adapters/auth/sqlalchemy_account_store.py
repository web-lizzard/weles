# pyright: reportUnusedParameter=false
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adapters.auth.model import Account, EmailAddress


class SqlAlchemyAccountStore:
    """`AccountStore` on Postgres. Auth has no application layer and no
    `UnitOfWork`: each `save` is one row in its own session and commit."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None: ...

    async def save(self, account: Account) -> None:
        """A unique-constraint violation on `email` becomes
        `EmailAlreadyRegisteredError`; the store never checks-then-inserts."""
        ...

    async def by_email(self, email: EmailAddress) -> Account | None: ...
