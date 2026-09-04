from domain.exceptions import CoreException


class DistillEmptyNoteContentError(CoreException):
    pass


class DistillNoteContentTooLongError(CoreException):
    pass


class EmptyCardSideError(CoreException):
    pass


class CardSideTooLongError(CoreException):
    pass


class EmptyAnchorError(CoreException):
    pass


class IdenticalCardSidesError(CoreException):
    pass


class InvalidDistillationTransitionError(CoreException):
    pass
