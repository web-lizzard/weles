from adapters.auth.authenticator import Authenticator
from adapters.auth.ports import SignInVerifier


def get_authenticator() -> Authenticator:
    """`SqlAlchemyAccountStore`, `PasswordHasher`, `PasswordPolicy` and
    `SignInTokens` (as issuer), built from the auth fields on `Settings`.
    Acceptance tests swap in `InMemoryAccountStore` through
    `dependency_overrides`."""
    ...


def get_sign_in_verifier() -> SignInVerifier:
    """The same `SignInTokens` instance the authenticator issues with, so a
    sign-in is recognised by the process whose secret signed it."""
    ...
