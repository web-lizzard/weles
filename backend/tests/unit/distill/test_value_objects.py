import pytest

from domain.distill.exceptions import (
    DistillEmptyNoteContentError,
    DistillNoteContentTooLongError,
)
from domain.distill.value_objects import NOTE_CONTENT_MAX_LENGTH, NoteContent


def test_note_content_empty_after_strip_raises_empty_note_content_error() -> None:
    with pytest.raises(DistillEmptyNoteContentError):
        _ = NoteContent(value="   ")


def test_note_content_over_max_length_raises_note_content_too_long_error() -> None:
    with pytest.raises(DistillNoteContentTooLongError):
        _ = NoteContent(value="a" * (NOTE_CONTENT_MAX_LENGTH + 1))


def test_note_content_stores_canonical_stripped_value() -> None:
    content = NoteContent(value="  Connections are established via handshakes.  ")

    assert content.value == "Connections are established via handshakes."
