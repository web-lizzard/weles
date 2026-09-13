# pyright: reportUnusedParameter=false
from adapters.auth.model import EmailAddress, IssuedSignIn, Password, PasswordPolicy
from adapters.auth.passwords import PasswordHasher
from adapters.auth.ports import AccountStore, SignInIssuer
from domain.shared.identity.model import UserId


class Authenticator:
    """Registration and sign-in. The HTTP router is its only caller; nothing in
    `domain/` or `application/` imports it."""

    def __init__(
        self,
        accounts: AccountStore,
        passwords: PasswordHasher,
        policy: PasswordPolicy,
        issuer: SignInIssuer,
    ) -> None: ...

    async def register(self, email: EmailAddress, password: Password) -> UserId:
        """policy.admit(password) -> passwords.hash -> Account.register ->
        accounts.save.

        Raises `PasswordTooShortError` before any hashing, and
        `EmailAlreadyRegisteredError` from the store. Issues no sign-in:
        registering and signing in are separate acts (AC-03).
        """
        ...

    async def sign_in(self, email: EmailAddress, password: Password) -> IssuedSignIn:
        """accounts.by_email -> passwords.verify -> issuer.issue(account.id).

        Raises `InvalidCredentialsError` for an unknown email and for a wrong
        password alike (AC-04).
        """
        ...
