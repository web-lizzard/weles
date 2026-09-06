from datetime import UTC, datetime, timedelta
from uuid import uuid4

from adapters.out.in_memory.distill.card_repository import InMemoryCardRepository
from adapters.out.in_memory.distill.list_notes_query import InMemoryListNotesQuery
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
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


def _note(
    status: DistillationStatus,
    updated_at: datetime,
    note_id: NoteId | None = None,
) -> Note:
    return Note(
        id=note_id or NoteId(value=uuid4()),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value="We discussed how connections are established."),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=status,
        approved_at=updated_at,
        created_at=updated_at,
        updated_at=updated_at,
    )


def _card(
    note_id: NoteId, created_at: datetime, discard: Discard | None = None
) -> Card:
    return Card(
        id=CardId(value=uuid4()),
        note_id=note_id,
        front=CardSide(value="What establishes a connection?"),
        back=CardSide(value="A three-way handshake."),
        anchor=Anchor(quote="Connections are established via a three-way handshake."),
        discard=discard,
        created_at=created_at,
    )


async def test_list_notes_returns_empty_list_when_no_notes_saved() -> None:
    query = InMemoryListNotesQuery(InMemoryNoteRepository(), InMemoryCardRepository())

    result = await query.list_notes()

    assert result == []


async def test_list_notes_exposes_raw_distillation_status_per_note() -> None:
    note_repository = InMemoryNoteRepository()
    now = datetime.now(UTC)
    generating = _note(DistillationStatus.GENERATING, now)
    ready = _note(DistillationStatus.READY, now)
    failed = _note(DistillationStatus.FAILED, now)
    for note in (generating, ready, failed):
        await note_repository.save(note)
    query = InMemoryListNotesQuery(note_repository, InMemoryCardRepository())

    result = await query.list_notes()

    statuses = {item.note_id: item.distillation_status for item in result}
    assert statuses[generating.id.value] == "generating"
    assert statuses[ready.id.value] == "ready"
    assert statuses[failed.id.value] == "failed"


async def test_list_notes_card_count_excludes_discarded_cards() -> None:
    note_repository = InMemoryNoteRepository()
    card_repository = InMemoryCardRepository()
    now = datetime.now(UTC)
    note = _note(DistillationStatus.READY, now)
    await note_repository.save(note)
    await card_repository.save(_card(note.id, now))
    await card_repository.save(_card(note.id, now))
    await card_repository.save(
        _card(
            note.id,
            now,
            discard=Discard(
                reason=DiscardReason.UNGROUNDED, detail=None, discarded_at=now
            ),
        )
    )
    query = InMemoryListNotesQuery(note_repository, card_repository)

    result = await query.list_notes()

    assert result[0].card_count == 2


async def test_list_notes_orders_by_recency_using_max_of_note_and_card_timestamps() -> (
    None
):
    note_repository = InMemoryNoteRepository()
    card_repository = InMemoryCardRepository()
    t1 = datetime.now(UTC)
    t3 = t1 + timedelta(minutes=3)
    t4 = t1 + timedelta(minutes=4)

    stale_by_own_timestamp_alone = _note(DistillationStatus.READY, t3)
    recent_only_because_of_its_card = _note(DistillationStatus.GENERATING, t1)
    await note_repository.save(stale_by_own_timestamp_alone)
    await note_repository.save(recent_only_because_of_its_card)
    await card_repository.save(_card(recent_only_because_of_its_card.id, t4))
    query = InMemoryListNotesQuery(note_repository, card_repository)

    result = await query.list_notes()

    assert result[0].note_id == recent_only_because_of_its_card.id.value
    assert result[1].note_id == stale_by_own_timestamp_alone.id.value
