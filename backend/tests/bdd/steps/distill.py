"""Step definitions for distill-flow acceptance scenarios."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from bdd.steps.approve_outbox import ApproveOutboxContext
from integration.support.in_memory_distill import (  # pyright: ignore[reportImplicitRelativeImport]
    InMemoryDistillComposition,
)
from pytest_bdd import given, then, when

from domain.distill.note import mint_note
from domain.distill.outbox import NoteSavedPayload
from domain.distill.value_objects import (
    DiscardReason,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)


@dataclass
class DistillFlowContext:
    seeded_note_id: UUID | None = None
    last_discarded_card_id: UUID | None = None


@pytest.fixture
def distill_flow_context() -> DistillFlowContext:
    return DistillFlowContext()


def _held_note_id(
    approve_outbox_context: ApproveOutboxContext,
    distill_flow_context: DistillFlowContext,
) -> UUID:
    if distill_flow_context.seeded_note_id is not None:
        return distill_flow_context.seeded_note_id
    assert approve_outbox_context.approval_response is not None
    return UUID(str(approve_outbox_context.approval_response["note_id"]))


@given("a held note whose content fits in a single sentence")
def a_held_note_single_sentence(
    distill_composition: InMemoryDistillComposition,
    distill_flow_context: DistillFlowContext,
) -> None:
    note_id = NoteId(value=uuid4())
    note = mint_note(
        note_id=note_id,
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="Single-sentence note"),
        content=NoteContent(value="Only one sentence lives in this note."),
        tags=[TagSnapshot(id=uuid4(), label="solo")],
        approved_at=datetime.now(UTC),
    )
    asyncio.run(distill_composition.notes.save(note))
    asyncio.run(
        distill_composition.outbox.append(
            NoteSavedPayload(note_id=note_id.value).to_envelope()
        )
    )
    distill_flow_context.seeded_note_id = note_id.value


@when("the distill worker drains the outbox once")
def distill_worker_drains_outbox_once(
    distill_composition: InMemoryDistillComposition,
) -> None:
    _ = asyncio.run(distill_composition.worker().run_once())


@then("the held note has at least one live card")
def held_note_has_at_least_one_live_card(
    distill_composition: InMemoryDistillComposition,
    approve_outbox_context: ApproveOutboxContext,
    distill_flow_context: DistillFlowContext,
) -> None:
    note_id = _held_note_id(approve_outbox_context, distill_flow_context)
    cards = asyncio.run(distill_composition.cards.list_by_note(NoteId(value=note_id)))
    assert any(card.discard is None for card in cards)


@then("the held note's distillation is ready")
def held_note_distillation_is_ready(
    distill_composition: InMemoryDistillComposition,
    approve_outbox_context: ApproveOutboxContext,
    distill_flow_context: DistillFlowContext,
) -> None:
    note_id = _held_note_id(approve_outbox_context, distill_flow_context)
    note = asyncio.run(distill_composition.notes.get(NoteId(value=note_id)))
    assert note is not None
    assert note.distillation_status == DistillationStatus.READY


@then("the held note has zero live cards")
def held_note_has_zero_live_cards(
    distill_composition: InMemoryDistillComposition,
    approve_outbox_context: ApproveOutboxContext,
    distill_flow_context: DistillFlowContext,
) -> None:
    note_id = _held_note_id(approve_outbox_context, distill_flow_context)
    cards = asyncio.run(distill_composition.cards.list_by_note(NoteId(value=note_id)))
    assert all(card.discard is not None for card in cards)


@then("every live card's quote resolves within the held note")
def every_live_card_quote_resolves(
    distill_composition: InMemoryDistillComposition,
    approve_outbox_context: ApproveOutboxContext,
    distill_flow_context: DistillFlowContext,
) -> None:
    note_id = _held_note_id(approve_outbox_context, distill_flow_context)
    note = asyncio.run(distill_composition.notes.get(NoteId(value=note_id)))
    assert note is not None
    cards = asyncio.run(distill_composition.cards.list_by_note(NoteId(value=note_id)))
    live = [card for card in cards if card.discard is None]
    assert live
    for card in live:
        assert asyncio.run(
            distill_composition.note_document_parser.resolves(
                note.content, card.anchor.quote
            )
        )


@then("the held note has a discarded card whose reason is ungrounded")
def held_note_has_ungrounded_discard(
    distill_composition: InMemoryDistillComposition,
    approve_outbox_context: ApproveOutboxContext,
    distill_flow_context: DistillFlowContext,
) -> None:
    note_id = _held_note_id(approve_outbox_context, distill_flow_context)
    cards = asyncio.run(distill_composition.cards.list_by_note(NoteId(value=note_id)))
    ungrounded = [
        card
        for card in cards
        if card.discard is not None and card.discard.reason == DiscardReason.UNGROUNDED
    ]
    assert ungrounded
    distill_flow_context.last_discarded_card_id = ungrounded[0].id.value


@then("that discarded card does not appear among the held note's live cards")
def discarded_card_not_among_live_cards(
    distill_composition: InMemoryDistillComposition,
    approve_outbox_context: ApproveOutboxContext,
    distill_flow_context: DistillFlowContext,
) -> None:
    note_id = _held_note_id(approve_outbox_context, distill_flow_context)
    cards = asyncio.run(distill_composition.cards.list_by_note(NoteId(value=note_id)))
    live_ids = {card.id.value for card in cards if card.discard is None}
    assert distill_flow_context.last_discarded_card_id not in live_ids
