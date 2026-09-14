"""Shared fixtures and builders for remember handler unit tests."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from integration.support.in_memory_remember import InMemoryRememberComposition

from adapters.out.fsrs.scheduler import PARAMETER_VERSION
from domain.distill.card import Card
from domain.distill.note import Note
from domain.distill.value_objects import (
    Anchor,
    CardSide,
    Discard,
    DiscardReason,
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TopicSnapshot,
)
from domain.distill.value_objects import (
    CardId as DistillCardId,
)
from domain.remember.ports import ReviewableCard
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    CardId,
    OpaqueSchedulerState,
    ResumeHorizon,
    SchedulerAlgorithm,
    SchedulerStamp,
    ShowingLimit,
)
from domain.shared.identity.model import UserId

OWNER: UserId = UserId.new()


class _Clock:
    def __init__(self, instant: datetime) -> None:
        self._instant: datetime = instant

    def now(self) -> datetime:
        return self._instant


@pytest.fixture
def make_composition() -> Callable[..., InMemoryRememberComposition]:
    """Build a fresh InMemoryRememberComposition pinned to a chosen instant."""

    def _make(
        instant: datetime | None = None,
        showing_limit: ShowingLimit | None = None,
        resume_horizon: ResumeHorizon | None = None,
    ) -> InMemoryRememberComposition:
        return InMemoryRememberComposition.create(
            clock=_Clock(instant or datetime.now(UTC)),
            showing_limit=showing_limit or ShowingLimit(value=2),
            resume_horizon=resume_horizon,
        )

    return _make


@pytest.fixture
def composition(
    make_composition: Callable[..., InMemoryRememberComposition],
) -> InMemoryRememberComposition:
    return make_composition()


def card_id() -> CardId:
    return CardId(value=uuid4())


async def reviewable(
    composition: InMemoryRememberComposition,
    *,
    id_: CardId | None = None,
    front: str = "What is TCP?",
    back: str = "A handshake.",
    discarded: bool = False,
) -> ReviewableCard:
    """Persist a distill note and card so the real catalog can serve it back."""
    chosen = id_ or card_id()
    now = datetime.now(UTC)
    note = Note(
        id=NoteId(value=uuid4()),
        owner_id=OWNER,
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="remember unit tests"),
        content=NoteContent(value=f"Note content backing {front}."),
        tags=[],
        distillation_status=DistillationStatus.READY,
        approved_at=now,
        created_at=now,
        updated_at=now,
    )
    card = Card(
        id=DistillCardId(value=chosen.value),
        owner_id=note.owner_id,
        note_id=note.id,
        front=CardSide(value=front),
        back=CardSide(value=back),
        anchor=Anchor(quote=f"Anchor backing {front}."),
        discard=Discard(reason=DiscardReason.USER_AUDIT, detail=None, discarded_at=now)
        if discarded
        else None,
        created_at=now,
    )
    await composition.notes.save(note)
    await composition.cards.save(card)
    return ReviewableCard(id=chosen, front=front, back=back)


def open_sitting(
    *cards: ReviewableCard, showing_limit: ShowingLimit | None = None
) -> Sitting:
    return open_sitting_for(OWNER, *cards, showing_limit=showing_limit)


def open_sitting_for(
    owner: UserId,
    *cards: ReviewableCard,
    showing_limit: ShowingLimit | None = None,
) -> Sitting:
    return Sitting.open(
        owner,
        frozenset(card.id for card in cards),
        datetime.now(UTC),
        showing_limit or ShowingLimit(value=2),
    )


def sitting_past_resume_horizon(
    *cards: ReviewableCard,
    opened_at: datetime,
    resume_horizon: ResumeHorizon,
    showing_limit: ShowingLimit | None = None,
) -> Sitting:
    """Sitting past horizon when the clock is at opened_at + 2h."""
    return Sitting.open(
        OWNER,
        frozenset(card.id for card in cards),
        opened_at,
        showing_limit or ShowingLimit(value=2),
        resume_horizon=resume_horizon,
    )


def clock_after_resume_horizon(opened_at: datetime) -> datetime:
    return opened_at + timedelta(hours=2)


def stamp(parameter_version: str = PARAMETER_VERSION) -> SchedulerStamp:
    return SchedulerStamp(
        algorithm=SchedulerAlgorithm.FSRS,
        parameter_version=parameter_version,
    )


def state(
    card_id_: CardId,
    *,
    due_at: datetime,
    stamp: SchedulerStamp,
    payload: dict[str, object] | None = None,
) -> SchedulingState:
    return SchedulingState(
        card_id=card_id_,
        due_at=due_at,
        scheduler_state=OpaqueSchedulerState(payload=payload or {}),
        stamp=stamp,
    )
