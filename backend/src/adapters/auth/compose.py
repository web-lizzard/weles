from datetime import timedelta

from adapters.auth.authenticator import Authenticator
from adapters.auth.model import (
    AttemptLimit,
    AttemptLimits,
    PasswordPolicy,
    SigningSecret,
    SignInLifetime,
)
from adapters.auth.passwords import PasswordHasher
from adapters.auth.ports import SignInVerifier
from adapters.auth.sqlalchemy_account_store import SqlAlchemyAccountStore
from adapters.auth.sqlalchemy_attempt_ledger import SqlAlchemyAttemptLedger
from adapters.auth.tokens import SignInTokens
from adapters.out.sqlalchemy.engine import create_engine, create_session_factory
from config.settings import Settings

_settings = Settings()  # pyright: ignore[reportCallIssue]

_engine = create_engine(_settings.database_url)
_session_factory = create_session_factory(_engine)

_accounts = SqlAlchemyAccountStore(_session_factory)

_attempt_limits = AttemptLimits(
    sign_in=AttemptLimit(
        max_attempts=_settings.auth_sign_in_max_failures,
        window=timedelta(minutes=_settings.auth_sign_in_failure_window_minutes),
    ),
    registration=AttemptLimit(
        max_attempts=_settings.auth_registration_max_attempts,
        window=timedelta(minutes=_settings.auth_registration_window_minutes),
    ),
)

_attempt_ledger = SqlAlchemyAttemptLedger(_session_factory, _attempt_limits)

_sign_in_tokens = SignInTokens(
    secret=SigningSecret(value=_settings.auth_signing_secret),
    lifetime=SignInLifetime(
        value=timedelta(hours=_settings.auth_sign_in_lifetime_hours)
    ),
    accounts=_accounts,
)

_authenticator = Authenticator(
    accounts=_accounts,
    passwords=PasswordHasher(),
    policy=PasswordPolicy(min_length=_settings.auth_password_min_length),
    issuer=_sign_in_tokens,
    attempts=_attempt_ledger,
)


def get_authenticator() -> Authenticator:
    """`SqlAlchemyAccountStore`, `PasswordHasher`, `PasswordPolicy` and
    `SignInTokens` (as issuer), built from the auth fields on `Settings`.
    Acceptance tests swap in `InMemoryAccountStore` through
    `dependency_overrides`."""
    return _authenticator


def get_sign_in_verifier() -> SignInVerifier:
    """The same `SignInTokens` instance the authenticator issues with, so a
    sign-in is recognised by the process whose secret signed it."""
    return _sign_in_tokens


def get_trusted_proxy_addresses() -> frozenset[str]:
    """Peer addresses allowed to set `X-Forwarded-For`, from `Settings`.
    Acceptance tests override this to trust `testclient`."""
    return frozenset(_settings.auth_trusted_proxy_addresses)
