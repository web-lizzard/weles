from datetime import timedelta

import pytest
from pydantic import SecretStr

from adapters.auth.authenticator import Authenticator
from adapters.auth.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    PasswordTooShortError,
    TooManyAttemptsError,
)
from adapters.auth.in_memory_account_store import InMemoryAccountStore
from adapters.auth.in_memory_attempt_ledger import InMemoryAttemptLedger
from adapters.auth.model import (
    DEFAULT_ATTEMPT_LIMITS,
    Account,
    AttemptLimit,
    AttemptLimits,
    AttemptSource,
    EmailAddress,
    Password,
    PasswordHash,
    PasswordPolicy,
    SigningSecret,
    SignInLifetime,
)
from adapters.auth.passwords import PasswordHasher
from adapters.auth.tokens import SignInTokens
from domain.shared.identity.model import UserId


def _sample_password() -> Password:
    return Password(value=SecretStr("long-enough-secret"))


def _sample_source() -> AttemptSource:
    return AttemptSource(value="203.0.113.1")


def _limits(max_attempts: int) -> AttemptLimits:
    limit = AttemptLimit(max_attempts=max_attempts, window=timedelta(minutes=15))
    return AttemptLimits(sign_in=limit, registration=limit)


def _authenticator(
    accounts: InMemoryAccountStore | None = None,
    *,
    limits: AttemptLimits | None = None,
) -> Authenticator:
    return Authenticator(
        accounts=accounts or InMemoryAccountStore(),
        passwords=PasswordHasher(),
        policy=PasswordPolicy(min_length=8),
        issuer=SignInTokens(
            secret=SigningSecret(value=SecretStr("a" * 32)),
            lifetime=SignInLifetime(value=timedelta(hours=1)),
            accounts=InMemoryAccountStore(),
        ),
        attempts=InMemoryAttemptLedger(limits or DEFAULT_ATTEMPT_LIMITS),
    )


async def test_register_returns_user_id_and_persists_account_without_a_token() -> None:
    accounts = InMemoryAccountStore()
    auth = _authenticator(accounts)
    email = EmailAddress.parse("alice@example.com")

    user_id = await auth.register(email, _sample_password(), _sample_source())

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
        _ = await auth.register(
            email, Password(value=SecretStr("short")), _sample_source()
        )

    assert await accounts.by_email(email) is None


async def test_register_raises_email_already_registered_for_canonical_email() -> None:
    auth = _authenticator()
    password = _sample_password()

    _ = await auth.register(
        EmailAddress.parse("alice@example.com"), password, _sample_source()
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        _ = await auth.register(
            EmailAddress.parse("Alice@example.com"), password, _sample_source()
        )


async def test_sign_in_returns_issued_sign_in_for_known_email_and_password() -> None:
    auth = _authenticator()
    email = EmailAddress.parse("alice@example.com")
    password = _sample_password()

    user_id = await auth.register(email, password, _sample_source())
    issued = await auth.sign_in(email, password, _sample_source())

    assert issued.user_id == user_id
    assert issued.token


async def test_sign_in_raises_invalid_credentials_error_for_unknown_email() -> None:
    auth = _authenticator()

    with pytest.raises(InvalidCredentialsError):
        _ = await auth.sign_in(
            EmailAddress.parse("nobody@example.com"),
            _sample_password(),
            _sample_source(),
        )


async def test_sign_in_raises_invalid_credentials_error_for_wrong_password() -> None:
    auth = _authenticator()
    email = EmailAddress.parse("alice@example.com")

    _ = await auth.register(email, _sample_password(), _sample_source())

    with pytest.raises(InvalidCredentialsError):
        _ = await auth.sign_in(
            email,
            Password(value=SecretStr("different-long-secret")),
            _sample_source(),
        )


async def test_sign_in_is_refused_at_the_limit_despite_a_right_password() -> None:
    accounts = InMemoryAccountStore()
    auth = _authenticator(accounts, limits=_limits(max_attempts=2))
    email = EmailAddress.parse("alice@example.com")
    _ = await auth.register(email, _sample_password(), _sample_source())
    wrong = Password(value=SecretStr("wrong-but-long-enough"))

    for _ in range(2):
        with pytest.raises(InvalidCredentialsError):
            _ = await auth.sign_in(email, wrong, _sample_source())

    with pytest.raises(TooManyAttemptsError):
        _ = await auth.sign_in(email, _sample_password(), _sample_source())


async def test_a_successful_sign_in_restores_the_sources_full_failure_allowance() -> (
    None
):
    accounts = InMemoryAccountStore()
    auth = _authenticator(accounts, limits=_limits(max_attempts=2))
    email = EmailAddress.parse("alice@example.com")
    _ = await auth.register(email, _sample_password(), _sample_source())
    wrong = Password(value=SecretStr("wrong-but-long-enough"))

    with pytest.raises(InvalidCredentialsError):
        _ = await auth.sign_in(email, wrong, _sample_source())
    _ = await auth.sign_in(email, _sample_password(), _sample_source())

    for _ in range(2):
        with pytest.raises(InvalidCredentialsError):
            _ = await auth.sign_in(email, wrong, _sample_source())

    with pytest.raises(TooManyAttemptsError):
        _ = await auth.sign_in(email, _sample_password(), _sample_source())


async def test_registration_beyond_the_limit_is_refused_and_persists_no_account() -> (
    None
):
    accounts = InMemoryAccountStore()
    auth = _authenticator(accounts, limits=_limits(max_attempts=2))
    for index in range(2):
        _ = await auth.register(
            EmailAddress.parse(f"alice{index}@example.com"),
            _sample_password(),
            _sample_source(),
        )
    refused = EmailAddress.parse("alice2@example.com")

    with pytest.raises(TooManyAttemptsError):
        _ = await auth.register(refused, _sample_password(), _sample_source())

    assert await accounts.by_email(refused) is None


async def test_registrations_refused_for_a_bad_password_or_taken_email_count() -> None:
    accounts = InMemoryAccountStore()
    taken = EmailAddress.parse("alice@example.com")
    await accounts.save(Account.register(taken, PasswordHash(value="opaque-hash")))
    auth = _authenticator(accounts, limits=_limits(max_attempts=2))

    with pytest.raises(PasswordTooShortError):
        _ = await auth.register(
            EmailAddress.parse("bob@example.com"),
            Password(value=SecretStr("short")),
            _sample_source(),
        )
    with pytest.raises(EmailAlreadyRegisteredError):
        _ = await auth.register(taken, _sample_password(), _sample_source())

    with pytest.raises(TooManyAttemptsError):
        _ = await auth.register(
            EmailAddress.parse("carol@example.com"),
            _sample_password(),
            _sample_source(),
        )
