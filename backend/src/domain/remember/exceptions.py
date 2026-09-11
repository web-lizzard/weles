from domain.exceptions import CoreException, NotFoundError


class EmptySittingError(CoreException):
    pass


class InvalidShowingLimitError(CoreException):
    pass


class InvalidResumeHorizonError(CoreException):
    pass


class SittingNotFoundError(NotFoundError):
    pass


class CardNotInSittingError(CoreException):
    pass


class CardNotPresentableError(CoreException):
    pass


class SittingAlreadyCompleteError(CoreException):
    pass


class SittingExpiredError(CoreException):
    pass


class CardNotReviewableError(NotFoundError):
    pass


class SourceNotAvailableError(NotFoundError):
    pass
