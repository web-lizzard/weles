from datetime import UTC, datetime

import pytest

from domain.capture.capture_session import CaptureSession
from domain.capture.exceptions import (
    CaptureSessionClosedError,
    NoteNotDraftError,
    NoteSessionMismatchError,
    SessionNoteAlreadyDraftedError,
    SessionNoteMissingError,
    SessionTopicAlreadyAssignedError,
    TagNotOnNoteError,
)
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    Embedding,
    Label,
    MessageContent,
    MessageId,
    MessageRole,
    NoteContent,
    NoteId,
    NoteStatus,
    SessionId,
    SessionStatus,
    SessionTopic,
    TagId,
    TopicId,
)


def test_start_creates_open_session_without_topic() -> None:
    session = CaptureSession.start()

    assert isinstance(session.id, SessionId)
    assert session.topic is None
    assert session.status == SessionStatus.OPEN
    assert isinstance(session.created_at, datetime)


def test_start_created_at_is_utc() -> None:
    """R1-F1: CaptureSession.start() must stamp created_at in UTC."""
    session = CaptureSession.start()

    assert session.created_at.tzinfo is UTC


def test_assign_topic_sets_topic_on_open_session() -> None:
    session = CaptureSession.start()
    topic = SessionTopic(value="TCP handshakes")

    session.assign_topic(topic)

    assert session.topic == topic


def test_assign_topic_raises_when_topic_already_set() -> None:
    session = CaptureSession.start()
    session.assign_topic(SessionTopic(value="TCP handshakes"))

    with pytest.raises(SessionTopicAlreadyAssignedError):
        session.assign_topic(SessionTopic(value="Something else"))


def test_record_creates_message_with_given_fields() -> None:
    session_id = SessionId.new()
    content = MessageContent(value="Let's talk about TCP handshakes")

    message = Message.record(
        session_id=session_id, role=MessageRole.USER, content=content
    )

    assert message.session_id == session_id
    assert message.role == MessageRole.USER
    assert message.content == content
    assert isinstance(message.id, MessageId)


def test_record_created_at_is_utc() -> None:
    """R1-F2: Message.record() must stamp created_at in UTC."""
    message = Message.record(
        session_id=SessionId.new(),
        role=MessageRole.USER,
        content=MessageContent(value="hello"),
    )

    assert message.created_at.tzinfo is UTC


def _minted_topic() -> Topic:
    return Topic(
        id=TopicId.new(),
        label=Label(value="TCP handshakes"),
        embedding=Embedding(values=(0.1, 0.2)),
        created_at=datetime.now(UTC),
    )


def _minted_tag(label: str = "networking") -> Tag:
    return Tag(
        id=TagId.new(),
        label=Label(value=label),
        embedding=Embedding(values=(0.3, 0.4)),
        created_at=datetime.now(UTC),
    )


def test_aggregate_factories_assign_ids_and_draft_shape() -> None:
    label = Label(value="TCP handshakes")
    embedding = Embedding(values=(0.1, 0.2))
    session_id = SessionId.new()
    content = NoteContent(value="We discussed how connections are established.")

    topic = Topic.mint(label, embedding)
    tag = Tag.mint(Label(value="networking"), Embedding(values=(0.3, 0.4)))
    note = Note.draft(session_id, topic, content, [tag])

    assert isinstance(topic.id, TopicId)
    assert topic.created_at.tzinfo is UTC
    assert isinstance(tag.id, TagId)
    assert tag.created_at.tzinfo is UTC
    assert note.session_id == session_id
    assert note.topic_id == topic.id
    assert note.tag_ids == [tag.id]
    assert note.content == content
    assert note.status == NoteStatus.DRAFT
    assert note.approved_at is None
    assert isinstance(note.id, NoteId)
    assert note.created_at.tzinfo is UTC


def test_draft_note_assigns_note_id_and_returns_drafted_note() -> None:
    session = CaptureSession.start()
    topic = _minted_topic()
    tag = _minted_tag()
    content = NoteContent(value="We discussed how connections are established.")

    note = session.draft_note(topic, content, [tag])

    assert session.note_id == note.id
    assert note.topic_id == topic.id
    assert note.tag_ids == [tag.id]
    assert note.status == NoteStatus.DRAFT


@pytest.mark.parametrize(
    ("session", "expected_error"),
    [
        pytest.param(
            CaptureSession(
                id=SessionId.new(),
                topic=None,
                note_id=None,
                status=SessionStatus.CLOSED,
                created_at=datetime.now(UTC),
            ),
            CaptureSessionClosedError,
            id="closed",
        ),
        pytest.param(
            CaptureSession(
                id=SessionId.new(),
                topic=None,
                note_id=NoteId.new(),
                status=SessionStatus.OPEN,
                created_at=datetime.now(UTC),
            ),
            SessionNoteAlreadyDraftedError,
            id="already_drafted",
        ),
    ],
)
def test_draft_note_raises_when_session_cannot_accept_note(
    session: CaptureSession,
    expected_error: type[CaptureSessionClosedError | SessionNoteAlreadyDraftedError],
) -> None:
    with pytest.raises(expected_error):
        _ = session.draft_note(
            _minted_topic(),
            NoteContent(value="We discussed how connections are established."),
            [_minted_tag()],
        )


def _drafted_session_with_note() -> tuple[CaptureSession, Note, Topic, Tag]:
    session = CaptureSession.start()
    topic = _minted_topic()
    tag = _minted_tag()
    note = session.draft_note(
        topic,
        NoteContent(value="We discussed how connections are established."),
        [tag],
    )
    return session, note, topic, tag


def test_note_mutators_raise_when_note_is_not_draft() -> None:
    _, note, _, tag = _drafted_session_with_note()
    approved = note.model_copy(update={"status": NoteStatus.APPROVED})
    replacement_topic = _minted_topic()
    extra_tag = _minted_tag("latency")

    with pytest.raises(NoteNotDraftError):
        approved.update_content(NoteContent(value="Revised content."))
    with pytest.raises(NoteNotDraftError):
        approved.change_topic(replacement_topic)
    with pytest.raises(NoteNotDraftError):
        approved.add_tag(extra_tag)
    with pytest.raises(NoteNotDraftError):
        approved.remove_tag(tag)


def test_note_topic_and_tag_mutators_update_fields() -> None:
    _, note, _, tag = _drafted_session_with_note()
    replacement_topic = _minted_topic()
    extra_tag = _minted_tag("latency")

    note.change_topic(replacement_topic)
    assert note.topic_id == replacement_topic.id

    note.add_tag(extra_tag)
    assert note.tag_ids == [tag.id, extra_tag.id]

    note.add_tag(extra_tag)
    assert note.tag_ids == [tag.id, extra_tag.id]

    note.remove_tag(tag)
    assert note.tag_ids == [extra_tag.id]

    with pytest.raises(TagNotOnNoteError):
        note.remove_tag(tag)


def test_note_approve_transitions_once_and_checks_session() -> None:
    session, note, _, _ = _drafted_session_with_note()
    wrong_session_id = SessionId.new()

    note.approve(session.id)

    assert note.status == NoteStatus.APPROVED
    assert note.approved_at is not None
    assert note.approved_at.tzinfo is UTC

    with pytest.raises(NoteNotDraftError):
        note.approve(session.id)

    _, fresh_note, _, _ = _drafted_session_with_note()
    with pytest.raises(NoteSessionMismatchError):
        fresh_note.approve(wrong_session_id)
    assert fresh_note.status == NoteStatus.DRAFT


def test_session_approve_closes_session_and_validates_note() -> None:
    session, note, _, _ = _drafted_session_with_note()

    session.approve(note)

    assert session.status == SessionStatus.CLOSED
    assert note.status == NoteStatus.APPROVED
    assert note.approved_at is not None

    with pytest.raises(CaptureSessionClosedError):
        session.approve(note)

    empty_session = CaptureSession.start()
    other_session, other_note, _, _ = _drafted_session_with_note()
    with pytest.raises(SessionNoteMissingError):
        empty_session.approve(other_note)

    mismatched_note = other_note.model_copy(update={"id": NoteId.new()})
    with pytest.raises(SessionNoteMissingError):
        other_session.approve(mismatched_note)
