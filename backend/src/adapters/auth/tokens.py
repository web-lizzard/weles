from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from adapters.auth.exceptions import AccountNoLongerExistsError, SignInRequiredError
from adapters.auth.model import IssuedSignIn, SigningSecret, SignInLifetime
from adapters.auth.ports import AccountStore
from domain.shared.identity.model import UserId


class SignInTokens:
    """The one implementation of `SignInIssuer` and `SignInVerifier`.

    Async underneath, but local for every token it refuses: neither issuing
    nor a refused `verify()` does network or disk I/O. A token that passes
    signature and expiry is confirmed against `AccountStore` before its
    `UserId` is returned, so `SignInTokens` is the implementation the port
    contract suite runs against on every CI invocation, with no second
    adapter.
    """

    def __init__(
        self, secret: SigningSecret, lifetime: SignInLifetime, accounts: AccountStore
    ) -> None:
        self._secret: str = secret.value.get_secret_value()
        self._lifetime: timedelta = lifetime.value
        self._accounts: AccountStore = accounts

    async def issue(self, user_id: UserId) -> IssuedSignIn:
        now = datetime.now(UTC)
        expires_at = now + self._lifetime
        token = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
            {"sub": str(user_id.value), "exp": expires_at},
            self._secret,
            algorithm="HS256",
        )
        if isinstance(token, bytes):
            token = token.decode()
        return IssuedSignIn(token=token, user_id=user_id, expires_at=expires_at)

    async def verify(self, token: str) -> UserId:
        try:
            payload = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
                token,
                self._secret,
                algorithms=["HS256"],
                options={"require": ["exp", "sub"]},
            )
        except jwt.PyJWTError:
            raise SignInRequiredError from None

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise SignInRequiredError
        try:
            user_id = UserId(value=UUID(sub))
        except ValueError:
            raise SignInRequiredError from None

        if not await self._accounts.exists(user_id):
            raise AccountNoLongerExistsError
        return user_id
