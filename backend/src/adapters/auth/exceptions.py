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


class PasswordMinimumBelowFloorError(CoreException):
    pass


class NonPositiveSignInLifetimeError(CoreException):
    pass


class SigningSecretTooShortError(CoreException):
    pass
