from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from adapters.auth.exceptions import SignInRequiredError
from adapters.auth.model import IssuedSignIn, SigningSecret, SignInLifetime
from domain.shared.identity.model import UserId


class SignInTokens:
    """The one implementation of `SignInIssuer` and `SignInVerifier`.

    Async underneath, but local: neither issuing nor verifying does network or
    disk I/O. That is what lets it be the implementation the port contract
    suite runs against on every CI invocation, with no second adapter.
    """

    def __init__(self, secret: SigningSecret, lifetime: SignInLifetime) -> None:
        self._secret: str = secret.value.get_secret_value()
        self._lifetime: timedelta = lifetime.value

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
            return UserId(value=UUID(sub))
        except ValueError:
            raise SignInRequiredError from None
