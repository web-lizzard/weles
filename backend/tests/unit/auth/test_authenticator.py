from datetime import timedelta

import pytest
from pydantic import SecretStr

from adapters.auth.authenticator import Authenticator
from adapters.auth.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    PasswordTooShortError,
)
from adapters.auth.in_memory_account_store import InMemoryAccountStore
from adapters.auth.model import (
    EmailAddress,
    Password,
    PasswordPolicy,
    SigningSecret,
    SignInLifetime,
)
from adapters.auth.passwords import PasswordHasher
from adapters.auth.tokens import SignInTokens
from domain.shared.identity.model import UserId


def _sample_password() -> Password:
    return Password(value=SecretStr("long-enough-secret"))


def _authenticator(accounts: InMemoryAccountStore | None = None) -> Authenticator:
    return Authenticator(
        accounts=accounts or InMemoryAccountStore(),
        passwords=PasswordHasher(),
        policy=PasswordPolicy(min_length=8),
        issuer=SignInTokens(
            secret=SigningSecret(value=SecretStr("a" * 32)),
            lifetime=SignInLifetime(value=timedelta(hours=1)),
        ),
    )


async def test_register_returns_user_id_and_persists_account_without_a_token() -> None:
    accounts = InMemoryAccountStore()
    auth = _authenticator(accounts)
    email = EmailAddress.parse("alice@example.com")

    user_id = await auth.register(email, _sample_password())

    assert isinstance(user_id, UserId)
    saved = await accounts.by_email(email)
    assert saved is not None
    assert saved.id == user_id


async def test_register_raises_password_too_short_error_before_persisting_account() -> (
    None
):
    accounts = InMemoryAccountStore()
    auth = _authenticator(accounts)
    email = EmailAddress.parse("alice@example.com")

    with pytest.raises(PasswordTooShortError):
        _ = await auth.register(email, Password(value=SecretStr("short")))

    assert await accounts.by_email(email) is None


async def test_register_raises_email_already_registered_for_canonical_email() -> None:
    auth = _authenticator()
    password = _sample_password()

    _ = await auth.register(EmailAddress.parse("alice@example.com"), password)

    with pytest.raises(EmailAlreadyRegisteredError):
        _ = await auth.register(EmailAddress.parse("Alice@example.com"), password)


async def test_sign_in_returns_issued_sign_in_for_known_email_and_password() -> None:
    auth = _authenticator()
    email = EmailAddress.parse("alice@example.com")
    password = _sample_password()

    user_id = await auth.register(email, password)
    issued = await auth.sign_in(email, password)

    assert issued.user_id == user_id
    assert issued.token


async def test_sign_in_raises_invalid_credentials_error_for_unknown_email() -> None:
    auth = _authenticator()

    with pytest.raises(InvalidCredentialsError):
        _ = await auth.sign_in(
            EmailAddress.parse("nobody@example.com"),
            _sample_password(),
        )


async def test_sign_in_raises_invalid_credentials_error_for_wrong_password() -> None:
    auth = _authenticator()
    email = EmailAddress.parse("alice@example.com")

    _ = await auth.register(email, _sample_password())

    with pytest.raises(InvalidCredentialsError):
        _ = await auth.sign_in(
            email,
            Password(value=SecretStr("different-long-secret")),
        )
