from datetime import timedelta

from adapters.auth.authenticator import Authenticator
from adapters.auth.model import PasswordPolicy, SigningSecret, SignInLifetime
from adapters.auth.passwords import PasswordHasher
from adapters.auth.ports import SignInVerifier
from adapters.auth.sqlalchemy_account_store import SqlAlchemyAccountStore
from adapters.auth.tokens import SignInTokens
from adapters.out.sqlalchemy.engine import create_engine, create_session_factory
from config.settings import Settings

_settings = Settings()  # pyright: ignore[reportCallIssue]

_engine = create_engine(_settings.database_url)
_session_factory = create_session_factory(_engine)

_accounts = SqlAlchemyAccountStore(_session_factory)

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
