from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import override

from pydantic import BaseModel, EmailStr, SecretStr, ValidationError

from adapters.auth.exceptions import (
    InvalidEmailAddressError,
    NonPositiveAttemptLimitError,
    NonPositiveSignInLifetimeError,
    PasswordMinimumBelowFloorError,
    PasswordTooShortError,
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
        stripped = raw.strip()
        try:
            validated = _EmailSyntax(value=stripped)
        except ValidationError as error:
            raise InvalidEmailAddressError from error
        return cls(value=validated.value.lower())


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
        if len(password.value.get_secret_value()) < self.min_length:
            raise PasswordTooShortError


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
        return cls(
            id=UserId.new(),
            email=email,
            password_hash=password_hash,
            created_at=datetime.now(UTC),
        )


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


class AttemptAction(StrEnum):
    """What kind of attempt is being counted."""

    SIGN_IN = "sign_in"
    REGISTRATION = "registration"


class AttemptSource(BaseModel, frozen=True):
    """Whoever is making the attempt, as resolved by `resolve_attempt_source`."""

    value: str


class AttemptLimit(BaseModel, frozen=True):
    """How many attempts of one action a source may make within a window."""

    max_attempts: int
    window: timedelta

    @override
    def model_post_init(self, _context: object) -> None:
        if self.max_attempts < 1 or self.window <= timedelta(0):
            raise NonPositiveAttemptLimitError


class AttemptLimits(BaseModel, frozen=True):
    """Per-instance configuration of both limited actions."""

    sign_in: AttemptLimit
    registration: AttemptLimit

    def for_action(self, action: AttemptAction) -> AttemptLimit:
        if action is AttemptAction.SIGN_IN:
            return self.sign_in
        return self.registration


DEFAULT_ATTEMPT_LIMITS = AttemptLimits(
    sign_in=AttemptLimit(max_attempts=5, window=timedelta(minutes=15)),
    registration=AttemptLimit(max_attempts=10, window=timedelta(minutes=60)),
)


class _EmailSyntax(BaseModel, frozen=True):
    """Private helper isolating `EmailStr` syntax validation behind a known
    field type, so `EmailAddress.parse` never surfaces `EmailStr`'s partially
    unknown generic to callers."""

    value: EmailStr
