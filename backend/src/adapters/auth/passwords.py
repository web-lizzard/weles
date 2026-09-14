import asyncio

from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

from adapters.auth.model import Password, PasswordHash


class PasswordHasher:
    """Deliberately slow, salted password hashing. Not a port: it does no I/O,
    so the real implementation is also the one tests run.

    Async because the work is CPU-bound and must not block the event loop.
    Only registration and sign-in call it; the sign-in gate never does.
    """

    def __init__(self) -> None:
        self._argon2: _Argon2Hasher = _Argon2Hasher()

    async def hash(self, password: Password) -> PasswordHash:
        raw = await asyncio.to_thread(
            self._argon2.hash, password.value.get_secret_value()
        )
        return PasswordHash(value=raw)

    async def verify(self, password: Password, password_hash: PasswordHash) -> bool:
        """False for a mismatch; never raises on a wrong password."""
        try:
            return await asyncio.to_thread(
                self._argon2.verify,
                password_hash.value,
                password.value.get_secret_value(),
            )
        except (VerifyMismatchError, VerificationError, InvalidHash):
            return False
