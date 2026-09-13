from adapters.out.sqlalchemy.capture.models import (
    CaptureMessageRow,
    CaptureNoteRow,
    CaptureNoteTagRow,
    CaptureSessionRow,
    CaptureTagRow,
    CaptureTopicRow,
)
from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Embedding


def capture_session_to_row(session: CaptureSession) -> CaptureSessionRow:
    return CaptureSessionRow(
        id=session.id,
        topic=session.topic,
        note_id=session.note_id,
        status=session.status,
        phase=session.phase,
        drafting_consent=session.drafting_consent,
        conversation_request=session.conversation_request,
        assessments=session.assessments,
        created_at=session.created_at,
        version=1,
    )


def capture_session_to_domain(row: CaptureSessionRow) -> CaptureSession:
    return CaptureSession(
        id=row.id,
        topic=row.topic,
        note_id=row.note_id,
        status=row.status,
        phase=row.phase,
        drafting_consent=row.drafting_consent,
        conversation_request=row.conversation_request,
        assessments=row.assessments,
        created_at=row.created_at,
    )


def message_to_row(message: Message) -> CaptureMessageRow:
    return CaptureMessageRow(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def message_to_domain(row: CaptureMessageRow) -> Message:
    return Message(
        id=row.id,
        session_id=row.session_id,
        role=row.role,
        content=row.content,
        created_at=row.created_at,
    )


def note_to_row(note: Note) -> CaptureNoteRow:
    return CaptureNoteRow(
        id=note.id,
        session_id=note.session_id,
        topic_id=note.topic_id,
        content=note.content,
        status=note.status,
        created_at=note.created_at,
        approved_at=note.approved_at,
        tags=[
            CaptureNoteTagRow(note_id=note.id, position=position, tag_id=tag_id)
            for position, tag_id in enumerate(note.tag_ids)
        ],
    )


def note_to_domain(row: CaptureNoteRow) -> Note:
    return Note(
        id=row.id,
        session_id=row.session_id,
        topic_id=row.topic_id,
        content=row.content,
        tag_ids=[tag.tag_id for tag in row.tags],
        status=row.status,
        created_at=row.created_at,
        approved_at=row.approved_at,
    )


def topic_to_row(topic: Topic) -> CaptureTopicRow:
    return CaptureTopicRow(
        id=topic.id,
        label=topic.label,
        embedding_values=topic.embedding.values,
        embedding_model=topic.embedding.model,
        created_at=topic.created_at,
    )


def topic_to_domain(row: CaptureTopicRow) -> Topic:
    return Topic(
        id=row.id,
        label=row.label,
        embedding=Embedding(values=row.embedding_values, model=row.embedding_model),
        created_at=row.created_at,
    )


def tag_to_row(tag: Tag) -> CaptureTagRow:
    return CaptureTagRow(
        id=tag.id,
        label=tag.label,
        embedding_values=tag.embedding.values,
        embedding_model=tag.embedding.model,
        created_at=tag.created_at,
    )


def tag_to_domain(row: CaptureTagRow) -> Tag:
    return Tag(
        id=row.id,
        label=row.label,
        embedding=Embedding(values=row.embedding_values, model=row.embedding_model),
        created_at=row.created_at,
    )
