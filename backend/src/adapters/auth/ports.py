from typing import Protocol

from adapters.auth.model import Account, EmailAddress, IssuedSignIn
from domain.shared.identity.model import UserId


class AccountStore(Protocol):
    """In-memory and Postgres implementations, one contract suite over both.

    `save` is the single place email uniqueness is enforced, so two concurrent
    registrations of the same address cannot both succeed.
    """

    async def save(self, account: Account) -> None:
        """Raises `EmailAlreadyRegisteredError` when a different account already
        holds `account.email`."""
        ...

    async def by_email(self, email: EmailAddress) -> Account | None: ...


class SignInIssuer(Protocol):
    """Issues sign-ins on behalf of this instance. Only `Authenticator.sign_in`
    holds one.

    An implementation owns its own key material and lifetime (constructor
    input, never a method argument), so no caller can issue a sign-in for a
    different instance or period.
    """

    async def issue(self, user_id: UserId) -> IssuedSignIn:
        """Expires the implementation's `SignInLifetime` from now."""
        ...


class SignInVerifier(Protocol):
    """Recognises sign-ins issued by this instance. Only the sign-in gate holds
    one; it cannot issue.

    Invariants every implementation holds (one contract suite over all):
    - Touches no database, account store, LLM, or network (PRD FR-009): an
      unidentified caller costs the instance nothing but CPU.
    - Yields a `UserId` only for a token this instance issued that has not yet
      expired; the `UserId` is the one it was issued for.
    - Nothing issued can be withdrawn before it expires.
    """

    async def verify(self, token: str) -> UserId:
        """Raises `SignInRequiredError` for a malformed, altered, made-up,
        foreign-instance, or expired token, with no distinction between them."""
        ...
