from domain.exceptions import CoreException


class DistillEmptyNoteContentError(CoreException):
    pass


class DistillNoteContentTooLongError(CoreException):
    pass
