from domain.exceptions import CoreException


class EnvelopeNotPendingError(CoreException):
    pass


class EnvelopeNotProcessingError(CoreException):
    pass
