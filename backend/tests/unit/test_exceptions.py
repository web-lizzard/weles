from typing import ClassVar

from domain.exceptions import CoreException


def test_code_derives_snake_case_stripped_of_trailing_error() -> None:
    class NoteNotFoundError(CoreException):
        pass

    assert NoteNotFoundError.code() == "note_not_found"


def test_code_strips_trailing_exception_suffix() -> None:
    class ValidationException(CoreException):
        pass

    assert ValidationException.code() == "validation"


def test_code_derives_snake_case_for_multi_word_class_name() -> None:
    class InvalidCaptureStateError(CoreException):
        pass

    assert InvalidCaptureStateError.code() == "invalid_capture_state"


def test_explicit_code_override_wins_over_derivation() -> None:
    class ConflictError(CoreException):
        _code: ClassVar[str] = "custom_conflict"

    assert ConflictError.code() == "custom_conflict"
