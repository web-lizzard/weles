from datetime import datetime

import pytest

from domain.capture.capture_session import CaptureSession
from domain.capture.exceptions import SessionTopicAlreadyAssignedError
from domain.capture.message import Message
from domain.capture.value_objects import (
    MessageContent,
    MessageId,
    MessageRole,
    SessionId,
    SessionStatus,
    Topic,
)


def test_start_creates_open_session_without_topic() -> None:
    session = CaptureSession.start()

    assert isinstance(session.id, SessionId)
    assert session.topic is None
    assert session.status == SessionStatus.OPEN
    assert isinstance(session.created_at, datetime)


def test_assign_topic_sets_topic_on_open_session() -> None:
    session = CaptureSession.start()
    topic = Topic(value="TCP handshakes")

    session.assign_topic(topic)

    assert session.topic == topic


def test_assign_topic_raises_when_topic_already_set() -> None:
    session = CaptureSession.start()
    session.assign_topic(Topic(value="TCP handshakes"))

    with pytest.raises(SessionTopicAlreadyAssignedError):
        session.assign_topic(Topic(value="Something else"))


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
