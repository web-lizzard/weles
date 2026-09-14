"""Step definitions for distill-flow note-list acceptance scenarios."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from bdd.conftest import NotesTestContext
from pytest_bdd import given, parsers, then, when

from domain.distill.card import Card
from domain.distill.note import Note, mint_note
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)
from domain.shared.identity.model import UserId


@dataclass
class NoteListContext:
    notes_client: NotesTestContext | None = None
    list_response: list[dict[str, object]] = field(default_factory=list)
    tracked_topic: str | None = None
    tracked_note_id: str | None = None
    older_note_id: str | None = None
    newer_note_id: str | None = None


@pytest.fixture
def note_list_context() -> NoteListContext:
    return NoteListContext()


def _anchor_quote() -> str:
    return "A quoted fragment from the note body."


def _live_card(note_id: NoteId, created_at: datetime) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        owner_id=UserId.new(),
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote=_anchor_quote()),
        discard=None,
        created_at=created_at,
    )


def _note_at(
    topic_label: str,
    status: DistillationStatus,
    at: datetime,
) -> Note:
    return Note(
        id=NoteId(value=uuid4()),
        owner_id=UserId.new(),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label=topic_label),
        content=NoteContent(value="Note body for acceptance scenarios."),
        tags=[TagSnapshot(id=uuid4(), label="bdd")],
        distillation_status=status,
        approved_at=at,
        created_at=at,
        updated_at=at,
    )


async def _save_note(
    notes_client: NotesTestContext,
    note: Note,
    live_card_count: int,
) -> None:
    await notes_client.notes.save(note)
    for offset in range(live_card_count):
        card_at = note.updated_at + timedelta(seconds=offset + 1)
        await notes_client.cards.save(_live_card(note.id, card_at))


@given("a running notes backend")
def running_notes_backend(
    notes_client: NotesTestContext,
    note_list_context: NoteListContext,
) -> None:
    note_list_context.notes_client = notes_client


@given(parsers.parse('a ready note titled "{topic}" with {card_count:d} live cards'))
def ready_note_titled_with_live_cards(
    notes_client: NotesTestContext,
    note_list_context: NoteListContext,
    topic: str,
    card_count: int,
) -> None:
    at = datetime.now(UTC)
    note = _note_at(topic, DistillationStatus.READY, at)
    asyncio.run(_save_note(notes_client, note, card_count))
    note_list_context.tracked_topic = topic
    note_list_context.tracked_note_id = str(note.id.value)


@given(parsers.parse('a generating note with topic "{topic}"'))
def generating_note_with_topic(
    notes_client: NotesTestContext,
    topic: str,
) -> None:
    note = mint_note(
        owner_id=UserId.new(),
        note_id=NoteId(value=uuid4()),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label=topic),
        content=NoteContent(value="Still generating."),
        tags=[TagSnapshot(id=uuid4(), label="bdd")],
        approved_at=datetime.now(UTC),
    )
    asyncio.run(_save_note(notes_client, note, 0))


@given(parsers.parse('a ready note with topic "{topic}" and zero live cards'))
def ready_note_with_zero_cards(
    notes_client: NotesTestContext,
    topic: str,
) -> None:
    note = _note_at(topic, DistillationStatus.READY, datetime.now(UTC))
    asyncio.run(_save_note(notes_client, note, 0))


@given(parsers.parse('a failed note with topic "{topic}"'))
def failed_note_with_topic(
    notes_client: NotesTestContext,
    topic: str,
) -> None:
    note = _note_at(topic, DistillationStatus.FAILED, datetime.now(UTC))
    asyncio.run(_save_note(notes_client, note, 0))


@given(parsers.parse('an older note with topic "{topic}"'))
def older_note_with_topic(
    notes_client: NotesTestContext,
    note_list_context: NoteListContext,
    topic: str,
) -> None:
    at = datetime.now(UTC) - timedelta(hours=1)
    note = _note_at(topic, DistillationStatus.READY, at)
    asyncio.run(_save_note(notes_client, note, 0))
    note_list_context.older_note_id = str(note.id.value)


@given(
    parsers.parse(
        'a newer note with topic "{topic}" touched more recently than the older note'
    )
)
def newer_note_touched_after_older(
    notes_client: NotesTestContext,
    note_list_context: NoteListContext,
    topic: str,
) -> None:
    at = datetime.now(UTC)
    note = _note_at(topic, DistillationStatus.GENERATING, at)
    asyncio.run(_save_note(notes_client, note, 0))
    note_list_context.newer_note_id = str(note.id.value)


@when("the user requests the note list")
def user_requests_note_list(note_list_context: NoteListContext) -> None:
    assert note_list_context.notes_client is not None
    response = note_list_context.notes_client.client.get("/notes")
    assert response.status_code == 200
    note_list_context.list_response = cast(list[dict[str, object]], response.json())


@then("that note appears in the list with topic, status, and card count")
def note_list_entry_shows_topic_status_and_count(
    note_list_context: NoteListContext,
) -> None:
    assert note_list_context.tracked_note_id is not None
    assert note_list_context.tracked_topic is not None
    entry = next(
        item
        for item in note_list_context.list_response
        if item["note_id"] == note_list_context.tracked_note_id
    )
    assert entry["topic_label"] == note_list_context.tracked_topic
    assert entry["distillation_status"] == "ready"
    assert entry["card_count"] == 2


@then("the list exposes generating, zero-card-ready, and failed states")
def note_list_shows_three_distillation_states(
    note_list_context: NoteListContext,
) -> None:
    by_topic = {
        str(item["topic_label"]): item for item in note_list_context.list_response
    }
    assert by_topic["In progress"]["distillation_status"] == "generating"
    assert by_topic["Empty result"]["distillation_status"] == "ready"
    assert by_topic["Empty result"]["card_count"] == 0
    assert by_topic["Broken run"]["distillation_status"] == "failed"


@then("the note list is ordered with the most recently touched note first")
def note_list_ordered_most_recent_first(
    note_list_context: NoteListContext,
) -> None:
    assert note_list_context.older_note_id is not None
    assert note_list_context.newer_note_id is not None
    note_ids = [str(item["note_id"]) for item in note_list_context.list_response]
    assert note_ids.index(note_list_context.newer_note_id) < note_ids.index(
        note_list_context.older_note_id
    )
