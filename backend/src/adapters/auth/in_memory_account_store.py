# pyright: reportUnusedParameter=false
from adapters.auth.model import Account, EmailAddress


class InMemoryAccountStore:
    """`AccountStore` for acceptance and unit tests. Holds the same email
    uniqueness guarantee as Postgres, including under concurrent `save`."""

    def __init__(self) -> None: ...

    async def save(self, account: Account) -> None: ...

    async def by_email(self, email: EmailAddress) -> Account | None: ...
