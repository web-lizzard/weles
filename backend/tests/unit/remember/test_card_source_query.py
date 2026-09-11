from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from integration.support.in_memory_remember import InMemoryRememberComposition

from adapters.out.in_memory.remember.card_source_locator import (
    InMemoryCardSourceLocator,
)
from application.remember.dto import CardSourceDTO
from application.remember.queries.card_source import CardSourceQuery
from domain.distill.card import Card
from domain.distill.note import Note
from domain.distill.value_objects import (
    Anchor,
    CardSide,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TopicSnapshot,
)
from domain.distill.value_objects import CardId as DistillCardId
from domain.remember.exceptions import (
    CardNotInSittingError,
    SittingExpiredError,
    SittingNotFoundError,
    SourceNotAvailableError,
)
from domain.remember.ports import ReviewableCard
from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, ResumeHorizon, Reveal, SittingId

from .conftest import (
    clock_after_resume_horizon,
    open_sitting,
    reviewable,
    sitting_past_resume_horizon,
)


def _query(composition: InMemoryRememberComposition) -> CardSourceQuery:
    locator = InMemoryCardSourceLocator(composition.notes, composition.cards)
    return CardSourceQuery(
        composition.sittings,
        composition.review_events,
        locator,
        composition.clock,
    )


async def _reviewable_with_resolvable_source(
    composition: InMemoryRememberComposition,
    *,
    note_body: str = "Connections are established via a three-way handshake.",
    anchor_quote: str = "Connections are established via a three-way handshake.",
    front: str = "What establishes a connection?",
    back: str = "A three-way handshake.",
) -> ReviewableCard:
    now = datetime.now(UTC)
    note = Note(
        id=NoteId(value=uuid4()),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="Networking"),
        content=NoteContent(value=note_body),
        tags=[],
        distillation_status=DistillationStatus.READY,
        approved_at=now,
        created_at=now,
        updated_at=now,
    )
    card = Card(
        id=DistillCardId(value=uuid4()),
        note_id=note.id,
        front=CardSide(value=front),
        back=CardSide(value=back),
        anchor=Anchor(quote=anchor_quote),
        discard=None,
        created_at=now,
    )
    await composition.notes.save(note)
    await composition.cards.save(card)
    return ReviewableCard(
        id=CardId(value=card.id.value),
        front=front,
        back=back,
    )


async def _save_reveal(
    composition: InMemoryRememberComposition,
    sitting_id: SittingId,
    card_id: CardId,
) -> None:
    event = ReviewEvent(
        card_id=card_id,
        reviewed_at=composition.clock.now(),
        payload=Reveal(),
        sitting_id=sitting_id,
    )
    await composition.review_events.save(event)


async def test_an_unknown_sitting_raises_sitting_not_found(
    composition: InMemoryRememberComposition,
) -> None:
    card = await reviewable(composition)

    with pytest.raises(SittingNotFoundError):
        _ = await _query(composition).handle(SittingId.new(), card.id)


async def test_a_sitting_past_its_horizon_raises_expired_on_source(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> None:
    opened_at = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
    horizon = ResumeHorizon(value=timedelta(hours=1))
    composition = make_composition(instant=clock_after_resume_horizon(opened_at))
    card = await reviewable(composition)
    sitting = sitting_past_resume_horizon(
        card, opened_at=opened_at, resume_horizon=horizon
    )
    await composition.sittings.save(sitting)

    with pytest.raises(SittingExpiredError):
        _ = await _query(composition).handle(sitting.id, card.id)


async def test_a_card_outside_the_sitting_raises_card_not_in_sitting(
    composition: InMemoryRememberComposition,
) -> None:
    member = await reviewable(composition)
    outsider = await reviewable(composition)
    sitting = open_sitting(member)
    await composition.sittings.save(sitting)

    with pytest.raises(CardNotInSittingError):
        _ = await _query(composition).handle(sitting.id, outsider.id)


async def test_a_card_with_no_reveal_event_raises_source_not_available(
    composition: InMemoryRememberComposition,
) -> None:
    card = await _reviewable_with_resolvable_source(composition)
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)

    with pytest.raises(SourceNotAvailableError):
        _ = await _query(composition).handle(sitting.id, card.id)


async def test_revealed_card_with_unresolvable_quote_raises_source_not_available(
    composition: InMemoryRememberComposition,
) -> None:
    card = await _reviewable_with_resolvable_source(
        composition,
        note_body="The note no longer contains the quoted passage.",
        anchor_quote="Connections are established via a three-way handshake.",
    )
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)
    await _save_reveal(composition, sitting.id, card.id)

    with pytest.raises(SourceNotAvailableError):
        _ = await _query(composition).handle(sitting.id, card.id)


async def test_after_reveal_a_resolvable_card_returns_blocks_and_span(
    composition: InMemoryRememberComposition,
) -> None:
    card = await _reviewable_with_resolvable_source(composition)
    sitting = open_sitting(card)
    await composition.sittings.save(sitting)
    await _save_reveal(composition, sitting.id, card.id)

    result = await _query(composition).handle(sitting.id, card.id)

    assert isinstance(result, CardSourceDTO)
    assert len(result.blocks) >= 1
    assert result.blocks[0].text
    assert result.span.block_index >= 0
    assert 0 <= result.span.start <= result.span.end
