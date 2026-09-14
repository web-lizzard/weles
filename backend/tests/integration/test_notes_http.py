from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from domain.distill.card import Card
from domain.distill.note import Note
from domain.distill.value_objects import (
    Anchor,
    CardId,
    CardSide,
    Discard,
    DiscardReason,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)
from domain.shared.identity.model import UserId

from .conftest import NotesTestContext


def _note(
    status: DistillationStatus,
    updated_at: datetime,
    caller: UserId,
    content: str = "We discussed how connections are established.",
) -> Note:
    return Note(
        id=NoteId(value=uuid4()),
        owner_id=caller,
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value=content),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=status,
        approved_at=updated_at,
        created_at=updated_at,
        updated_at=updated_at,
    )


def _card(
    note_id: NoteId,
    created_at: datetime,
    caller: UserId,
    discard: Discard | None = None,
    quote: str = "Connections are established via a three-way handshake.",
    front: str = "What establishes a connection?",
) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        owner_id=caller,
        note_id=note_id,
        front=CardSide(value=front),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote=quote),
        discard=discard,
        created_at=created_at,
    )


async def test_get_notes_returns_seeded_notes_shaped_and_ordered_by_recency(
    notes_client: NotesTestContext,
) -> None:
    now = datetime.now(UTC)
    caller = notes_client.caller
    older = _note(DistillationStatus.READY, now, caller)
    newer = _note(DistillationStatus.GENERATING, now + timedelta(minutes=5), caller)
    await notes_client.notes.save(older)
    await notes_client.notes.save(newer)
    await notes_client.cards.save(_card(older.id, now, caller))

    response = notes_client.client.get("/notes")

    assert response.status_code == 200
    body = cast(list[dict[str, object]], response.json())
    assert [item["note_id"] for item in body] == [
        str(newer.id.value),
        str(older.id.value),
    ]
    assert body[1]["topic_label"] == older.topic.label
    assert body[1]["distillation_status"] == "ready"
    assert body[1]["card_count"] == 1


async def test_get_notes_returns_empty_list_when_no_notes_saved(
    notes_client: NotesTestContext,
) -> None:
    response = notes_client.client.get("/notes")

    assert response.status_code == 200
    assert response.json() == []


async def test_get_note_returns_seeded_note_shaped_for_a_known_id(
    notes_client: NotesTestContext,
) -> None:
    now = datetime.now(UTC)
    caller = notes_client.caller
    note = _note(DistillationStatus.READY, now, caller)
    await notes_client.notes.save(note)

    response = notes_client.client.get(f"/notes/{note.id.value}")

    assert response.status_code == 200
    body = cast(dict[str, object], response.json())
    assert body["note_id"] == str(note.id.value)
    assert body["topic"] == {"id": str(note.topic.id), "label": note.topic.label}
    assert body["content"] == note.content.value
    assert body["tags"] == [
        {"id": str(tag.id), "label": tag.label} for tag in note.tags
    ]
    assert body["distillation_status"] == "ready"


async def test_get_note_returns_404_for_an_unknown_note_id(
    notes_client: NotesTestContext,
) -> None:
    response = notes_client.client.get(f"/notes/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == "distill_note_not_found"


async def test_get_cards_for_note_returns_live_cards_ordered_by_created_at(
    notes_client: NotesTestContext,
) -> None:
    now = datetime.now(UTC)
    caller = notes_client.caller
    note = _note(DistillationStatus.READY, now, caller)
    await notes_client.notes.save(note)
    older = _card(note.id, now, caller)
    newer = _card(note.id, now + timedelta(minutes=5), caller)
    await notes_client.cards.save(newer)
    await notes_client.cards.save(older)

    response = notes_client.client.get(f"/notes/{note.id.value}/cards")

    assert response.status_code == 200
    body = cast(list[dict[str, object]], response.json())
    assert [item["card_id"] for item in body] == [
        str(older.id.value),
        str(newer.id.value),
    ]
    assert body[0]["front"] == older.front.value
    assert body[0]["back"] == older.back.value
    assert body[0]["anchor_quote"] == older.anchor.quote


async def test_get_cards_for_note_returns_empty_list_when_all_cards_are_discarded(
    notes_client: NotesTestContext,
) -> None:
    now = datetime.now(UTC)
    caller = notes_client.caller
    note = _note(DistillationStatus.READY, now, caller)
    await notes_client.notes.save(note)
    await notes_client.cards.save(
        _card(
            note.id,
            now,
            caller,
            discard=Discard(
                reason=DiscardReason.UNGROUNDED, detail=None, discarded_at=now
            ),
        )
    )

    response = notes_client.client.get(f"/notes/{note.id.value}/cards")

    assert response.status_code == 200
    assert response.json() == []


async def test_get_cards_for_note_returns_empty_list_for_a_ready_note_with_no_cards(
    notes_client: NotesTestContext,
) -> None:
    caller = notes_client.caller
    note = _note(DistillationStatus.READY, datetime.now(UTC), caller)
    await notes_client.notes.save(note)

    response = notes_client.client.get(f"/notes/{note.id.value}/cards")

    assert response.status_code == 200
    assert response.json() == []


async def test_get_cards_for_note_returns_404_for_an_unknown_note_id(
    notes_client: NotesTestContext,
) -> None:
    response = notes_client.client.get(f"/notes/{uuid4()}/cards")

    assert response.status_code == 404
    assert response.json()["code"] == "distill_note_not_found"


async def test_get_note_returns_blocks_in_document_order_with_raw_text(
    notes_client: NotesTestContext,
) -> None:
    now = datetime.now(UTC)
    content = "# TCP Handshake\n\nThe client sends SYN.\n\nThe server replies SYN-ACK."
    caller = notes_client.caller
    note = _note(DistillationStatus.READY, now, caller, content=content)
    await notes_client.notes.save(note)

    response = notes_client.client.get(f"/notes/{note.id.value}")

    assert response.status_code == 200
    body = cast(dict[str, object], response.json())
    assert body["content"] == content
    assert body["blocks"] == [
        {"index": 0, "text": "# TCP Handshake"},
        {"index": 1, "text": "The client sends SYN."},
        {"index": 2, "text": "The server replies SYN-ACK."},
    ]


async def test_get_cards_for_note_returns_exact_block_and_unresolved_locations(
    notes_client: NotesTestContext,
) -> None:
    now = datetime.now(UTC)
    content = "# TCP Handshake\n\nThe client sends SYN and waits."
    exact_quote = "The client sends SYN and waits."
    heading_quote = "TCP Handshake"
    missing_quote = "a fragment that is no longer in this note"
    caller = notes_client.caller
    note = _note(DistillationStatus.READY, now, caller, content=content)
    await notes_client.notes.save(note)
    await notes_client.cards.save(
        _card(
            note.id, now, caller, quote=exact_quote, front="What does the client send?"
        )
    )
    await notes_client.cards.save(
        _card(
            note.id,
            now + timedelta(seconds=1),
            caller,
            quote=heading_quote,
            front="What is the heading?",
        )
    )
    await notes_client.cards.save(
        _card(
            note.id,
            now + timedelta(seconds=2),
            caller,
            quote=missing_quote,
            front="What is missing?",
        )
    )

    note_response = notes_client.client.get(f"/notes/{note.id.value}")
    cards_response = notes_client.client.get(f"/notes/{note.id.value}/cards")

    assert note_response.status_code == 200
    assert cards_response.status_code == 200
    note_body = cast(dict[str, object], note_response.json())
    cards = cast(list[dict[str, object]], cards_response.json())
    blocks = cast(list[dict[str, object]], note_body["blocks"])
    by_quote = {str(item["anchor_quote"]): item for item in cards}

    exact_location = by_quote[exact_quote]["anchor_location"]
    assert exact_location is not None
    exact_location = cast(dict[str, object], exact_location)
    exact_block = cast(str, blocks[cast(int, exact_location["block_index"])]["text"])
    start = cast(int, exact_location["start"])
    end = cast(int, exact_location["end"])
    assert exact_location["precision"] == "exact"
    assert exact_block[start:end] == exact_quote

    block_location = by_quote[heading_quote]["anchor_location"]
    assert block_location is not None
    block_location = cast(dict[str, object], block_location)
    heading_block = cast(str, blocks[cast(int, block_location["block_index"])]["text"])
    assert block_location["precision"] == "block"
    assert block_location["start"] == 0
    assert block_location["end"] == len(heading_block)

    assert by_quote[missing_quote]["anchor_location"] is None
