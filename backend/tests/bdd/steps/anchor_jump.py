"""Step definitions for US-07 card-to-anchor-jump acceptance scenarios."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from bdd.conftest import NotesTestContext
from pytest_bdd import given, parsers, then, when

from domain.distill.card import Card
from domain.distill.note import Note
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
class AnchorJumpContext:
    note_id: str | None = None
    card_id: str | None = None
    note_content: str | None = None
    quote: str | None = None
    note_response: dict[str, object] | None = None
    cards_response: list[dict[str, object]] = field(default_factory=list)


@pytest.fixture
def anchor_jump_context() -> AnchorJumpContext:
    return AnchorJumpContext()


def _ready_note(content: str) -> Note:
    at = datetime.now(UTC)
    return Note(
        id=NoteId(value=uuid4()),
        owner_id=UserId.new(),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="Anchor jump"),
        content=NoteContent(value=content),
        tags=[TagSnapshot(id=uuid4(), label="bdd")],
        distillation_status=DistillationStatus.READY,
        approved_at=at,
        created_at=at,
        updated_at=at,
    )


def _live_card(note_id: NoteId, quote: str, created_at: datetime) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        owner_id=UserId.new(),
        note_id=note_id,
        front=CardSide(value="What does this card ask?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote=quote),
        discard=None,
        created_at=created_at,
    )


def _tracked_card(anchor_jump_context: AnchorJumpContext) -> dict[str, object]:
    assert anchor_jump_context.card_id is not None
    return next(
        item
        for item in anchor_jump_context.cards_response
        if item["card_id"] == anchor_jump_context.card_id
    )


@given(parsers.parse('a ready note containing "{body}"'))
def ready_note_containing(
    notes_client: NotesTestContext,
    anchor_jump_context: AnchorJumpContext,
    body: str,
) -> None:
    note = _ready_note(body)
    asyncio.run(notes_client.notes.save(note))
    anchor_jump_context.note_id = str(note.id.value)
    anchor_jump_context.note_content = note.content.value


@given(parsers.parse('a ready note headed "{heading}"'))
def ready_note_headed(
    notes_client: NotesTestContext,
    anchor_jump_context: AnchorJumpContext,
    heading: str,
) -> None:
    note = _ready_note(f"# {heading}")
    asyncio.run(notes_client.notes.save(note))
    anchor_jump_context.note_id = str(note.id.value)
    anchor_jump_context.note_content = note.content.value


@given(parsers.parse('a live card quoting "{quote}"'))
def live_card_quoting(
    notes_client: NotesTestContext,
    anchor_jump_context: AnchorJumpContext,
    quote: str,
) -> None:
    assert anchor_jump_context.note_id is not None
    card = _live_card(
        NoteId(value=UUID(anchor_jump_context.note_id)),
        quote,
        datetime.now(UTC),
    )
    asyncio.run(notes_client.cards.save(card))
    anchor_jump_context.card_id = str(card.id.value)
    anchor_jump_context.quote = quote


@when("the user requests that note")
def user_requests_that_note(
    notes_client: NotesTestContext,
    anchor_jump_context: AnchorJumpContext,
) -> None:
    assert anchor_jump_context.note_id is not None
    response = notes_client.client.get(f"/notes/{anchor_jump_context.note_id}")
    assert response.status_code == 200
    anchor_jump_context.note_response = cast(dict[str, object], response.json())


@when("the user requests that note's cards")
def user_requests_that_notes_cards(
    notes_client: NotesTestContext,
    anchor_jump_context: AnchorJumpContext,
) -> None:
    assert anchor_jump_context.note_id is not None
    response = notes_client.client.get(f"/notes/{anchor_jump_context.note_id}/cards")
    assert response.status_code == 200
    anchor_jump_context.cards_response = cast(list[dict[str, object]], response.json())


@then("that card's location points at the quoted passage")
def card_location_points_at_quoted_passage(
    anchor_jump_context: AnchorJumpContext,
) -> None:
    assert anchor_jump_context.quote is not None
    location = _tracked_card(anchor_jump_context)["anchor_location"]
    assert location is not None
    location = cast(dict[str, object], location)
    assert location["precision"] == "exact"
    assert location["block_index"] == 0
    assert location["start"] == 0
    assert location["end"] == len(anchor_jump_context.quote)


@then("that card's location covers the whole heading block")
def card_location_covers_heading_block(
    anchor_jump_context: AnchorJumpContext,
) -> None:
    assert anchor_jump_context.note_content is not None
    location = _tracked_card(anchor_jump_context)["anchor_location"]
    assert location is not None
    location = cast(dict[str, object], location)
    assert location["precision"] == "block"
    assert location["block_index"] == 0
    assert location["start"] == 0
    assert location["end"] == len(anchor_jump_context.note_content)


@then("the held note is still readable")
def held_note_is_still_readable(
    anchor_jump_context: AnchorJumpContext,
) -> None:
    assert anchor_jump_context.note_response is not None
    assert anchor_jump_context.note_content is not None
    assert anchor_jump_context.note_response["content"] == (
        anchor_jump_context.note_content
    )
    blocks = cast(list[dict[str, object]], anchor_jump_context.note_response["blocks"])
    assert blocks
    assert blocks[0]["index"] == 0
    assert blocks[0]["text"] == anchor_jump_context.note_content


@then("that card reports no location")
def card_reports_no_location(
    anchor_jump_context: AnchorJumpContext,
) -> None:
    assert _tracked_card(anchor_jump_context)["anchor_location"] is None
