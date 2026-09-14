from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.auth.exceptions import EmailAlreadyRegisteredError
from adapters.auth.in_memory_account_store import InMemoryAccountStore
from adapters.auth.model import Account, EmailAddress, PasswordHash
from adapters.auth.ports import AccountStore
from adapters.auth.sqlalchemy_account_store import SqlAlchemyAccountStore
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.shared.identity.model import UserId


@dataclass
class _AccountFixture:
    store: AccountStore


def _password_hash(value: str = "opaque-hash") -> PasswordHash:
    return PasswordHash(value=value)


def _account(email: str = "alice@example.com") -> Account:
    return Account.register(
        email=EmailAddress.parse(email),
        password_hash=_password_hash(),
    )


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def account_fixture(request: pytest.FixtureRequest) -> _AccountFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return _AccountFixture(store=InMemoryAccountStore())
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _AccountFixture(store=SqlAlchemyAccountStore(session_factory))


async def test_by_email_returns_a_saved_account_for_an_equal_email_address(
    account_fixture: _AccountFixture,
) -> None:
    account = _account()
    lookup = EmailAddress.parse("ALICE@example.com")

    await account_fixture.store.save(account)
    result = await account_fixture.store.by_email(lookup)

    assert result == account


async def test_by_email_returns_none_for_an_unknown_email(
    account_fixture: _AccountFixture,
) -> None:
    result = await account_fixture.store.by_email(
        EmailAddress.parse("nobody@example.com")
    )

    assert result is None


async def test_save_raises_email_already_registered_for_duplicate_canonical_email(
    account_fixture: _AccountFixture,
) -> None:
    email = EmailAddress.parse("alice@example.com")
    first = Account.register(email=email, password_hash=_password_hash())
    second = Account.register(email=email, password_hash=_password_hash("other-hash"))

    await account_fixture.store.save(first)

    with pytest.raises(EmailAlreadyRegisteredError):
        await account_fixture.store.save(second)


async def test_exists_returns_true_for_a_saved_accounts_id(
    account_fixture: _AccountFixture,
) -> None:
    account = _account()

    await account_fixture.store.save(account)
    result = await account_fixture.store.exists(account.id)

    assert result is True


async def test_exists_returns_false_for_an_unknown_user_id(
    account_fixture: _AccountFixture,
) -> None:
    result = await account_fixture.store.exists(UserId.new())

    assert result is False
