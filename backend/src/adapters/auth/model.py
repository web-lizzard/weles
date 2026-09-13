# pyright: reportUnusedParameter=false
from datetime import datetime, timedelta
from typing import override

from pydantic import BaseModel, SecretStr

from adapters.auth.exceptions import (
    NonPositiveSignInLifetimeError,
    PasswordMinimumBelowFloorError,
    SigningSecretTooShortError,
)
from domain.shared.identity.model import UserId

PASSWORD_MIN_LENGTH_FLOOR = 8
SIGNING_SECRET_MIN_BYTES = 32


class EmailAddress(BaseModel, frozen=True):
    """A syntactically valid email address, already in its one canonical form.

    Invariant: two addresses that differ only in letter case, anywhere in the
    address, or in surrounding whitespace produce equal `EmailAddress` values.
    `parse` is the only way to build one from caller input, so equality here is
    identity of a person for registration and sign-in.
    """

    value: str

    @classmethod
    def parse(cls, raw: str) -> "EmailAddress":
        """Validate syntax as Pydantic's `EmailStr` does, then case-fold the
        whole address (EmailStr lowercases the domain only).

        Raises `InvalidEmailAddressError`.
        """
        ...


class Password(BaseModel, frozen=True):
    """A password exactly as the caller sent it. Never logged, never stored."""

    value: SecretStr


class PasswordPolicy(BaseModel, frozen=True):
    """The instance's password minimum. The operator may raise it, never lower
    it below `PASSWORD_MIN_LENGTH_FLOOR`."""

    min_length: int

    @override
    def model_post_init(self, _context: object) -> None:
        if self.min_length < PASSWORD_MIN_LENGTH_FLOOR:
            raise PasswordMinimumBelowFloorError

    def admit(self, password: Password) -> None:
        """Raises `PasswordTooShortError` when the password is shorter than
        `min_length`."""
        ...


class PasswordHash(BaseModel, frozen=True):
    """Opaque output of `PasswordHasher.hash`; only the hasher reads it."""

    value: str


class Account(BaseModel, frozen=True):
    """What the auth adapter keeps about a person. Only `id` crosses into the
    core."""

    id: UserId
    email: EmailAddress
    password_hash: PasswordHash
    created_at: datetime

    @classmethod
    def register(cls, email: EmailAddress, password_hash: PasswordHash) -> "Account":
        """A fresh `UserId` and `created_at` of now."""
        ...


class SigningSecret(BaseModel, frozen=True):
    """The instance's own means of issuing sign-ins.

    Required configuration with no default: nothing in the public repository,
    image, or TUI can produce a sign-in an instance accepts.
    """

    value: SecretStr

    @override
    def model_post_init(self, _context: object) -> None:
        if len(self.value.get_secret_value().encode()) < SIGNING_SECRET_MIN_BYTES:
            raise SigningSecretTooShortError


class SignInLifetime(BaseModel, frozen=True):
    """How long an issued sign-in stays accepted. Per instance, default one day
    (set in `Settings`)."""

    value: timedelta

    @override
    def model_post_init(self, _context: object) -> None:
        if self.value <= timedelta(0):
            raise NonPositiveSignInLifetimeError


class IssuedSignIn(BaseModel, frozen=True):
    token: str
    user_id: UserId
    expires_at: datetime
