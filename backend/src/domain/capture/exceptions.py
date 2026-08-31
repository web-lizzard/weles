from domain.exceptions import CoreException


class EmptySessionTopicError(CoreException):
    pass


class SessionTopicTooLongError(CoreException):
    pass


class EmptyMessageContentError(CoreException):
    pass


class MessageContentTooLongError(CoreException):
    pass


class CaptureSessionNotFoundError(CoreException):
    pass


class CaptureSessionClosedError(CoreException):
    pass


class SessionTopicAlreadyAssignedError(CoreException):
    pass
