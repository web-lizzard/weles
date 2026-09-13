from domain.exceptions import CoreException


class EmptyConfidencePointError(CoreException):
    pass


class CaptureSessionConflictError(CoreException):
    pass
