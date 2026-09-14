from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

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
from domain.remember.outbox import CARD_REJECTED
from domain.shared.identity.model import UserId

from .conftest import RememberTestContext


def _note() -> Note:
    now = datetime.now(UTC)
    return Note(
        id=NoteId(value=uuid4()),
        owner_id=UserId.new(),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(
            value="Connections are established via a three-way handshake."
        ),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=DistillationStatus.READY,
        approved_at=now,
        created_at=now,
        updated_at=now,
    )


def _card(
    note_id: NoteId,
    front: str = "What establishes a connection?",
    back: str = "A three-way handshake.",
) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        owner_id=UserId.new(),
        note_id=note_id,
        front=CardSide(value=front),
        back=CardSide(value=back),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=None,
        created_at=datetime.now(UTC),
    )


async def test_full_review_loop_returns_a_front_reveals_it_and_completes_on_grade(
    remember_client: RememberTestContext,
) -> None:
    note = _note()
    card = _card(note.id)
    await remember_client.notes.save(note)
    await remember_client.cards.save(card)

    opened = remember_client.client.post("/review-sittings")

    assert opened.status_code == 200
    opened_body = cast(dict[str, object], opened.json())
    assert opened_body["kind"] == "opened"
    assert opened_body["card_id"] == str(card.id.value)
    assert opened_body["front"] == card.front.value
    sitting_id = cast(str, opened_body["sitting_id"])

    current = remember_client.client.get(f"/review-sittings/{sitting_id}/current-card")

    assert current.status_code == 200
    current_body = cast(dict[str, object], current.json())
    assert current_body["card_id"] == str(card.id.value)
    assert current_body["front"] == card.front.value

    back = remember_client.client.post(
        f"/review-sittings/{sitting_id}/cards/{card.id.value}/back"
    )

    assert back.status_code == 200
    assert cast(dict[str, object], back.json())["back"] == card.back.value

    graded = remember_client.client.post(
        f"/review-sittings/{sitting_id}/cards/{card.id.value}/grade",
        json={"grade": "good"},
    )

    assert graded.status_code == 200
    graded_body = cast(dict[str, object], graded.json())
    assert graded_body["sitting_complete"] is True
    assert graded_body["next_card_id"] is None
    assert graded_body["next_front"] is None


async def test_open_sitting_returns_nothing_due_when_no_cards_are_reviewable(
    remember_client: RememberTestContext,
) -> None:
    response = remember_client.client.post("/review-sittings")

    assert response.status_code == 200
    assert response.json() == {"kind": "nothing_due"}


async def test_get_due_cards_count_returns_a_live_partition_for_seeded_cards(
    remember_client: RememberTestContext,
) -> None:
    note = _note()
    card = _card(note.id)
    await remember_client.notes.save(note)
    await remember_client.cards.save(card)

    response = remember_client.client.get("/due-cards/count")

    assert response.status_code == 200
    body = cast(dict[str, object], response.json())
    due = cast(dict[str, object], body["due"])
    assert due["total"] == 1
    assert due["not_yet_seen"] == 1
    assert due["seen_still_owed"] == 0
    assert due["ripe_outside_sitting"] == 0


async def test_current_card_returns_404_for_an_unknown_sitting_id(
    remember_client: RememberTestContext,
) -> None:
    unknown_sitting_id = UUID("00000000-0000-4000-8000-000000000001")

    response = remember_client.client.get(
        f"/review-sittings/{unknown_sitting_id}/current-card"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "sitting_not_found"


async def test_grade_card_returns_409_for_a_card_that_is_not_the_one_in_front(
    remember_client: RememberTestContext,
) -> None:
    note = _note()
    card_a = _card(note.id, front="Card A front")
    card_b = _card(note.id, front="Card B front")
    await remember_client.notes.save(note)
    await remember_client.cards.save(card_a)
    await remember_client.cards.save(card_b)

    opened = remember_client.client.post("/review-sittings")
    opened_body = cast(dict[str, object], opened.json())
    sitting_id = cast(str, opened_body["sitting_id"])
    presented_card_id = cast(str, opened_body["card_id"])
    other_card_id = (
        card_b.id.value
        if presented_card_id == str(card_a.id.value)
        else card_a.id.value
    )

    response = remember_client.client.post(
        f"/review-sittings/{sitting_id}/cards/{other_card_id}/grade",
        json={"grade": "good"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "card_not_presentable"


async def test_reject_card_returns_204_and_queues_card_rejected_on_the_remember_outbox(
    remember_client: RememberTestContext,
) -> None:
    note = _note()
    card = _card(note.id)
    await remember_client.notes.save(note)
    await remember_client.cards.save(card)

    opened = remember_client.client.post("/review-sittings")
    opened_body = cast(dict[str, object], opened.json())
    sitting_id = cast(str, opened_body["sitting_id"])
    card_id = cast(str, opened_body["card_id"])

    response = remember_client.client.post(
        f"/review-sittings/{sitting_id}/cards/{card_id}/rejection"
    )

    assert response.status_code == 204
    assert response.content == b""

    envelopes = remember_client.outbox_store.all()
    assert len(envelopes) == 1
    assert envelopes[0].type == CARD_REJECTED
    assert envelopes[0].payload["card_id"] == card_id


async def test_source_route_returns_404_before_the_back_is_revealed(
    remember_client: RememberTestContext,
) -> None:
    note = _note()
    card = _card(note.id)
    await remember_client.notes.save(note)
    await remember_client.cards.save(card)

    opened = remember_client.client.post("/review-sittings")
    opened_body = cast(dict[str, object], opened.json())
    sitting_id = cast(str, opened_body["sitting_id"])
    card_id = cast(str, opened_body["card_id"])

    response = remember_client.client.get(
        f"/review-sittings/{sitting_id}/cards/{card_id}/source"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "source_not_available"


async def test_source_route_returns_blocks_and_span_after_the_back_is_revealed(
    remember_client: RememberTestContext,
) -> None:
    note = _note()
    card = _card(note.id)
    await remember_client.notes.save(note)
    await remember_client.cards.save(card)

    opened = remember_client.client.post("/review-sittings")
    opened_body = cast(dict[str, object], opened.json())
    sitting_id = cast(str, opened_body["sitting_id"])
    card_id = cast(str, opened_body["card_id"])

    reveal = remember_client.client.post(
        f"/review-sittings/{sitting_id}/cards/{card_id}/back"
    )
    assert reveal.status_code == 200

    response = remember_client.client.get(
        f"/review-sittings/{sitting_id}/cards/{card_id}/source"
    )

    assert response.status_code == 200
    body = cast(dict[str, object], response.json())
    blocks = cast(list[object], body["blocks"])
    span = cast(dict[str, object], body["span"])
    assert len(blocks) >= 1
    assert isinstance(blocks[0], dict)
    assert "text" in cast(dict[str, object], blocks[0])
    assert "block_index" in span
    assert "start" in span
    assert "end" in span
