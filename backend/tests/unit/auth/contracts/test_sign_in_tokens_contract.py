import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from adapters.auth.exceptions import AccountNoLongerExistsError, SignInRequiredError
from adapters.auth.in_memory_account_store import InMemoryAccountStore
from adapters.auth.model import (
    Account,
    EmailAddress,
    PasswordHash,
    SigningSecret,
    SignInLifetime,
)
from adapters.auth.ports import AccountStore, SignInIssuer, SignInVerifier
from adapters.auth.tokens import SignInTokens
from domain.shared.identity.model import UserId

_DEFAULT_LIFETIME = SignInLifetime(value=timedelta(hours=1))


def _secret(value: str = "a" * 32) -> SigningSecret:
    return SigningSecret(value=SecretStr(value))


def _account(user_id: UserId) -> Account:
    return Account(
        id=user_id,
        email=EmailAddress.parse(f"{user_id.value}@example.com"),
        password_hash=PasswordHash(value="opaque-hash"),
        created_at=datetime.now(UTC),
    )


@dataclass
class _TokenFixture:
    issuer: SignInIssuer
    verifier: SignInVerifier
    accounts: AccountStore
    build: Callable[[SigningSecret, SignInLifetime, AccountStore], SignInTokens]


def _build_local(
    secret: SigningSecret, lifetime: SignInLifetime, accounts: AccountStore
) -> SignInTokens:
    return SignInTokens(secret=secret, lifetime=lifetime, accounts=accounts)


@pytest.fixture(params=["local"], ids=["local"])
def token_fixture(
    request: pytest.FixtureRequest,  # pyright: ignore[reportUnusedParameter]
) -> _TokenFixture:
    accounts = InMemoryAccountStore()
    tokens = _build_local(_secret(), _DEFAULT_LIFETIME, accounts)
    return _TokenFixture(
        issuer=tokens, verifier=tokens, accounts=accounts, build=_build_local
    )


async def test_verify_returns_the_user_id_a_token_was_issued_for(
    token_fixture: _TokenFixture,
) -> None:
    user_id = UserId.new()
    await token_fixture.accounts.save(_account(user_id))

    issued = await token_fixture.issuer.issue(user_id)
    result = await token_fixture.verifier.verify(issued.token)

    assert result == user_id


async def test_verify_raises_account_no_longer_exists_error_when_the_account_is_gone(
    token_fixture: _TokenFixture,
) -> None:
    user_id = UserId.new()
    await token_fixture.accounts.save(_account(user_id))
    issued = await token_fixture.issuer.issue(user_id)

    stranded = token_fixture.build(_secret(), _DEFAULT_LIFETIME, InMemoryAccountStore())

    with pytest.raises(AccountNoLongerExistsError):
        _ = await stranded.verify(issued.token)


async def test_verify_raises_sign_in_required_error_for_a_token_from_another_secret(
    token_fixture: _TokenFixture,
) -> None:
    other = token_fixture.build(
        _secret("b" * 32), _DEFAULT_LIFETIME, InMemoryAccountStore()
    )
    issued = await other.issue(UserId.new())

    with pytest.raises(SignInRequiredError):
        _ = await token_fixture.verifier.verify(issued.token)


async def test_verify_raises_sign_in_required_error_for_an_altered_token(
    token_fixture: _TokenFixture,
) -> None:
    issued = await token_fixture.issuer.issue(UserId.new())
    last = issued.token[-1]
    altered = issued.token[:-1] + ("0" if last != "0" else "1")

    with pytest.raises(SignInRequiredError):
        _ = await token_fixture.verifier.verify(altered)


async def test_verify_raises_sign_in_required_error_for_a_made_up_string(
    token_fixture: _TokenFixture,
) -> None:
    with pytest.raises(SignInRequiredError):
        _ = await token_fixture.verifier.verify("not-a-real-token")


async def test_verify_raises_sign_in_required_error_for_a_token_past_its_lifetime(
    token_fixture: _TokenFixture,
) -> None:
    short_lived = token_fixture.build(
        _secret(),
        SignInLifetime(value=timedelta(microseconds=1)),
        InMemoryAccountStore(),
    )

    issued = await short_lived.issue(UserId.new())
    await asyncio.sleep(0.01)

    with pytest.raises(SignInRequiredError):
        _ = await short_lived.verify(issued.token)
