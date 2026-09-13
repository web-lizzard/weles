# pyright: reportUnusedParameter=false
from adapters.auth.model import Password, PasswordHash


class PasswordHasher:
    """Deliberately slow, salted password hashing. Not a port: it does no I/O,
    so the real implementation is also the one tests run.

    Async because the work is CPU-bound and must not block the event loop.
    Only registration and sign-in call it; the sign-in gate never does.
    """

    async def hash(self, password: Password) -> PasswordHash: ...

    async def verify(self, password: Password, password_hash: PasswordHash) -> bool:
        """False for a mismatch; never raises on a wrong password."""
        ...
