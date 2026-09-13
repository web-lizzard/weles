import pytest

from domain.distill.exceptions import (
    DistillEmptyNoteContentError,
    DistillNoteContentTooLongError,
)
from domain.distill.value_objects import (
    NOTE_CONTENT_MAX_LENGTH,
    NoteContent,
    ReviewGrade,
)


def test_note_content_empty_after_strip_raises_empty_note_content_error() -> None:
    with pytest.raises(DistillEmptyNoteContentError):
        _ = NoteContent(value="   ")


def test_note_content_over_max_length_raises_note_content_too_long_error() -> None:
    with pytest.raises(DistillNoteContentTooLongError):
        _ = NoteContent(value="a" * (NOTE_CONTENT_MAX_LENGTH + 1))


def test_note_content_stores_canonical_stripped_value() -> None:
    content = NoteContent(value="  Connections are established via handshakes.  ")

    assert content.value == "Connections are established via handshakes."


def test_review_grade_rank_rises_from_poor_to_strong() -> None:
    assert [grade.rank for grade in ReviewGrade] == [0, 1, 2, 3]


def test_only_sound_and_strong_grades_pass() -> None:
    assert [grade.passes for grade in ReviewGrade] == [False, False, True, True]
