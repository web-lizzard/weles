from domain.exceptions import CoreException


class EmptyConfidencePointError(CoreException):
    pass


class DraftTopicMissingError(CoreException):
    pass
