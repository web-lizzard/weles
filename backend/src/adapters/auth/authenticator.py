# pyright: reportUnusedParameter=false
from adapters.auth.exceptions import InvalidCredentialsError
from adapters.auth.model import (
    Account,
    AttemptSource,
    EmailAddress,
    IssuedSignIn,
    Password,
    PasswordPolicy,
)
from adapters.auth.passwords import PasswordHasher
from adapters.auth.ports import AccountStore, AttemptLedger, SignInIssuer
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
        attempts: AttemptLedger,
    ) -> None:
        self._accounts: AccountStore = accounts
        self._passwords: PasswordHasher = passwords
        self._policy: PasswordPolicy = policy
        self._issuer: SignInIssuer = issuer
        self._attempts: AttemptLedger = attempts

    async def register(
        self, email: EmailAddress, password: Password, source: AttemptSource
    ) -> UserId:
        """policy.admit(password) -> passwords.hash -> Account.register ->
        accounts.save.

        Raises `PasswordTooShortError` before any hashing, and
        `EmailAlreadyRegisteredError` from the store. Issues no sign-in:
        registering and signing in are separate acts (AC-03).

        Ignores `attempts` and `source` for now (Phase 4 wires limiting).
        """
        self._policy.admit(password)
        password_hash = await self._passwords.hash(password)
        account = Account.register(email, password_hash)
        await self._accounts.save(account)
        return account.id

    async def sign_in(
        self, email: EmailAddress, password: Password, source: AttemptSource
    ) -> IssuedSignIn:
        """accounts.by_email -> passwords.verify -> issuer.issue(account.id).

        Raises `InvalidCredentialsError` for an unknown email and for a wrong
        password alike (AC-04).

        Ignores `attempts` and `source` for now (Phase 4 wires limiting).
        """
        account = await self._accounts.by_email(email)
        if account is None:
            raise InvalidCredentialsError
        if not await self._passwords.verify(password, account.password_hash):
            raise InvalidCredentialsError
        return await self._issuer.issue(account.id)
