# pyright: reportUnusedParameter=false
from adapters.auth.model import IssuedSignIn, SigningSecret, SignInLifetime
from domain.shared.identity.model import UserId


class SignInTokens:
    """The one implementation of `SignInIssuer` and `SignInVerifier`.

    Async underneath, but local: neither issuing nor verifying does network or
    disk I/O. That is what lets it be the implementation the port contract
    suite runs against on every CI invocation, with no second adapter.
    """

    def __init__(self, secret: SigningSecret, lifetime: SignInLifetime) -> None: ...

    async def issue(self, user_id: UserId) -> IssuedSignIn: ...

    async def verify(self, token: str) -> UserId: ...
