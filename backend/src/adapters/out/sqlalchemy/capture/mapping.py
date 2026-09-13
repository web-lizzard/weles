from adapters.out.sqlalchemy.capture.models import (
    CaptureMessageRow,
    CaptureNoteRow,
    CaptureSessionRow,
    CaptureTagRow,
    CaptureTopicRow,
)
from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic


def capture_session_to_row(_session: CaptureSession) -> CaptureSessionRow:
    raise NotImplementedError


def capture_session_to_domain(_row: CaptureSessionRow) -> CaptureSession:
    raise NotImplementedError


def message_to_row(_message: Message) -> CaptureMessageRow:
    raise NotImplementedError


def message_to_domain(_row: CaptureMessageRow) -> Message:
    raise NotImplementedError


def note_to_row(_note: Note) -> CaptureNoteRow:
    raise NotImplementedError


def note_to_domain(_row: CaptureNoteRow) -> Note:
    raise NotImplementedError


def topic_to_row(_topic: Topic) -> CaptureTopicRow:
    raise NotImplementedError


def topic_to_domain(_row: CaptureTopicRow) -> Topic:
    raise NotImplementedError


def tag_to_row(_tag: Tag) -> CaptureTagRow:
    raise NotImplementedError


def tag_to_domain(_row: CaptureTagRow) -> Tag:
    raise NotImplementedError
