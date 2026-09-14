from adapters.auth.exceptions import InvalidCredentialsError
from adapters.auth.model import (
    Account,
    AttemptAction,
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
        """attempts.ensure_allowed -> attempts.record -> policy.admit(password)
        -> passwords.hash -> Account.register -> accounts.save.

        Raises `TooManyAttemptsError` before any hashing or store access, once
        `source` has reached its registration limit. Otherwise every attempt
        that reaches this point is recorded before the S-01 flow runs, so a
        refused registration (short password, taken email) still counts.

        Raises `PasswordTooShortError` before any hashing, and
        `EmailAlreadyRegisteredError` from the store. Issues no sign-in:
        registering and signing in are separate acts (AC-03).
        """
        await self._attempts.ensure_allowed(AttemptAction.REGISTRATION, source)
        await self._attempts.record(AttemptAction.REGISTRATION, source)
        self._policy.admit(password)
        password_hash = await self._passwords.hash(password)
        account = Account.register(email, password_hash)
        await self._accounts.save(account)
        return account.id

    async def sign_in(
        self, email: EmailAddress, password: Password, source: AttemptSource
    ) -> IssuedSignIn:
        """attempts.ensure_allowed -> accounts.by_email -> passwords.verify ->
        issuer.issue(account.id).

        Raises `TooManyAttemptsError` before any store read or password
        hashing, once `source` has reached its sign-in failure limit.

        Raises `InvalidCredentialsError` for an unknown email and for a wrong
        password alike (AC-04), recording the failure against `source` before
        re-raising. A successful sign-in clears `source`'s recorded failures.
        """
        await self._attempts.ensure_allowed(AttemptAction.SIGN_IN, source)
        account = await self._accounts.by_email(email)
        if account is None:
            await self._attempts.record(AttemptAction.SIGN_IN, source)
            raise InvalidCredentialsError
        if not await self._passwords.verify(password, account.password_hash):
            await self._attempts.record(AttemptAction.SIGN_IN, source)
            raise InvalidCredentialsError
        await self._attempts.clear(AttemptAction.SIGN_IN, source)
        return await self._issuer.issue(account.id)
