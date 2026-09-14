from domain.exceptions import CoreException


class InvalidEmailAddressError(CoreException):
    pass


class PasswordTooShortError(CoreException):
    pass


class EmailAlreadyRegisteredError(CoreException):
    pass


class InvalidCredentialsError(CoreException):
    """Raised for an unknown email and for a wrong password alike (AC-04)."""


class SignInRequiredError(CoreException):
    """Raised for a missing, malformed, altered, made-up, or expired sign-in
    alike. The caller learns only that it is not signed in."""


class AccountNoLongerExistsError(CoreException):
    """Raised for a structurally valid, unexpired token whose account is no
    longer in the store. Kept apart from `SignInRequiredError` for
    internal/log-level differentiation only; both remain an opaque sign-in
    refusal to the caller."""


class PasswordMinimumBelowFloorError(CoreException):
    pass


class NonPositiveSignInLifetimeError(CoreException):
    pass


class SigningSecretTooShortError(CoreException):
    pass


class TooManyAttemptsError(CoreException):
    """Raised by `AttemptLedger.ensure_allowed` once a source's attempts of one
    action reach the configured limit within the window."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__()
        self.retry_after_seconds: int = retry_after_seconds


class NonPositiveAttemptLimitError(CoreException):
    pass
