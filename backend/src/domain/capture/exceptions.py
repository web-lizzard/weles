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


class EmptyLabelError(CoreException):
    pass


class LabelTooLongError(CoreException):
    pass


class EmptyEmbeddingError(CoreException):
    pass


class EmptyEmbeddingModelError(CoreException):
    pass


class EmbeddingComponentOutOfRangeError(CoreException):
    pass


class EmptyNoteContentError(CoreException):
    pass


class NoteContentTooLongError(CoreException):
    pass


class SessionNoteAlreadyDraftedError(CoreException):
    pass


class NoteNotDraftError(CoreException):
    pass


class NoteSessionMismatchError(CoreException):
    pass


class SessionNoteMissingError(CoreException):
    pass


class NoteNotFoundError(CoreException):
    pass


class TagNotOnNoteError(CoreException):
    pass


class NoteVocabularyIncompleteError(CoreException):
    pass


class SimilarityScoreOutOfRangeError(CoreException):
    pass


class CoverageOutOfRangeError(CoreException):
    pass


class EmbeddingDimensionMismatchError(CoreException):
    pass


class ZeroMagnitudeEmbeddingError(CoreException):
    pass


class DraftTopicMissingError(CoreException):
    pass
