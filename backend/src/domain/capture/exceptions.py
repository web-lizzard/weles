from domain.exceptions import CoreException


class EmptyTopicError(CoreException):
    pass


class TopicTooLongError(CoreException):
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
