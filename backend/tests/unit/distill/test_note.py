from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from domain.distill.exceptions import InvalidDistillationTransitionError
from domain.distill.note import Note, mint_note
from domain.distill.value_objects import (
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)
from domain.shared.identity.model import UserId


def test_mint_note_maps_every_field_and_starts_generating() -> None:
    owner_id = UserId.new()
    note_id = NoteId(value=uuid4())
    session_id = SessionId(value=uuid4())
    topic = TopicSnapshot(id=uuid4(), label="TCP handshakes")
    content = NoteContent(value="We discussed how connections are established.")
    tags = [TagSnapshot(id=uuid4(), label="networking")]
    approved_at = datetime.now(UTC)

    note = mint_note(owner_id, note_id, session_id, topic, content, tags, approved_at)

    assert note.id == note_id
    assert note.owner_id == owner_id
    assert note.session_id == session_id
    assert note.topic == topic
    assert note.content == content
    assert note.tags == tags
    assert note.distillation_status == DistillationStatus.GENERATING
    assert note.approved_at == approved_at


def test_mint_note_stamps_created_at_in_utc_near_now() -> None:
    before = datetime.now(UTC)

    note = mint_note(
        UserId.new(),
        NoteId(value=uuid4()),
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        NoteContent(value="We discussed how connections are established."),
        [],
        before,
    )

    after = datetime.now(UTC)

    assert note.created_at.tzinfo is UTC
    assert before <= note.created_at <= after


def _note_in(status: DistillationStatus) -> Note:
    note = mint_note(
        UserId.new(),
        NoteId(value=uuid4()),
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        NoteContent(value="We discussed how connections are established."),
        [],
        datetime.now(UTC),
    )
    return note.model_copy(update={"distillation_status": status})


def test_mark_ready_moves_a_generating_note_to_ready() -> None:
    note = _note_in(DistillationStatus.GENERATING)

    note.mark_ready()

    assert note.distillation_status is DistillationStatus.READY


def test_mark_failed_moves_a_generating_note_to_failed() -> None:
    note = _note_in(DistillationStatus.GENERATING)

    note.mark_failed()

    assert note.distillation_status is DistillationStatus.FAILED


@pytest.mark.parametrize(
    "transition",
    [
        pytest.param(Note.mark_ready, id="mark_ready"),
        pytest.param(Note.mark_failed, id="mark_failed"),
    ],
)
@pytest.mark.parametrize(
    "status",
    [
        pytest.param(DistillationStatus.READY, id="from_ready"),
        pytest.param(DistillationStatus.FAILED, id="from_failed"),
    ],
)
def test_a_note_that_is_no_longer_generating_refuses_a_transition(
    status: DistillationStatus,
    transition: Callable[[Note], None],
) -> None:
    note = _note_in(status)

    with pytest.raises(InvalidDistillationTransitionError):
        transition(note)

    assert note.distillation_status is status


def test_mint_note_sets_updated_at_equal_to_created_at() -> None:
    note = mint_note(
        UserId.new(),
        NoteId(value=uuid4()),
        SessionId(value=uuid4()),
        TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        NoteContent(value="We discussed how connections are established."),
        [],
        datetime.now(UTC),
    )

    assert note.updated_at == note.created_at


@pytest.mark.parametrize(
    "transition",
    [
        pytest.param(Note.mark_ready, id="mark_ready"),
        pytest.param(Note.mark_failed, id="mark_failed"),
    ],
)
def test_a_legal_transition_bumps_updated_at_forward(
    transition: Callable[[Note], None],
) -> None:
    note = _note_in(DistillationStatus.GENERATING)
    previous_updated_at = note.updated_at

    transition(note)

    assert note.updated_at > previous_updated_at


@pytest.mark.parametrize(
    "transition",
    [
        pytest.param(Note.mark_ready, id="mark_ready"),
        pytest.param(Note.mark_failed, id="mark_failed"),
    ],
)
@pytest.mark.parametrize(
    "status",
    [
        pytest.param(DistillationStatus.READY, id="from_ready"),
        pytest.param(DistillationStatus.FAILED, id="from_failed"),
    ],
)
def test_a_refused_transition_does_not_bump_updated_at(
    status: DistillationStatus,
    transition: Callable[[Note], None],
) -> None:
    note = _note_in(status)
    previous_updated_at = note.updated_at

    with pytest.raises(InvalidDistillationTransitionError):
        transition(note)

    assert note.updated_at == previous_updated_at
