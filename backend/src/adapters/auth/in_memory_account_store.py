import asyncio

from adapters.auth.exceptions import EmailAlreadyRegisteredError
from adapters.auth.model import Account, EmailAddress


class InMemoryAccountStore:
    """`AccountStore` for acceptance and unit tests. Holds the same email
    uniqueness guarantee as Postgres, including under concurrent `save`."""

    def __init__(self) -> None:
        self._accounts: dict[EmailAddress, Account] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def save(self, account: Account) -> None:
        async with self._lock:
            existing = self._accounts.get(account.email)
            if existing is not None and existing.id != account.id:
                raise EmailAlreadyRegisteredError
            self._accounts[account.email] = account

    async def by_email(self, email: EmailAddress) -> Account | None:
        async with self._lock:
            return self._accounts.get(email)
