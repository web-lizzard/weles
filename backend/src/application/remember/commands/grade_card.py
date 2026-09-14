from collections.abc import Callable, Mapping, Sequence

from application.remember.dto import DuePartitionDTO, GradeAppliedDTO
from application.remember.ports import Clock, UnitOfWork
from domain.remember.due_partition import partition_due
from domain.remember.exceptions import SittingNotFoundError
from domain.remember.ports import (
    ReviewableCard,
    ReviewCatalog,
    Scheduler,
    SchedulingReplay,
)
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import CardId, Grade, Graded, SittingId
from domain.shared.identity.model import UserId


class GradeCardCommand:
    def __init__(
        self,
        uow_factory: Callable[[UserId], UnitOfWork],
        catalog: ReviewCatalog,
        scheduler: Scheduler,
        clock: Clock,
    ) -> None:
        self._uow_factory: Callable[[UserId], UnitOfWork] = uow_factory
        self._catalog: ReviewCatalog = catalog
        self._scheduler: Scheduler = scheduler
        self._clock: Clock = clock

    async def handle(
        self, owner: UserId, sitting_id: SittingId, card_id: CardId, grade: Grade
    ) -> GradeAppliedDTO:
        """Record a grade on the card in front and return the next front, or completion.

        Captures the clock once for both the event and the scheduler. Guards
        membership, completion, and presentability before any write. Previous
        scheduling state is the memoized record when its stamp matches, otherwise
        a replay of the card's log. The event and memoized state are written
        together in one unit of work. ShowingLimit comes from the sitting, not
        compose.
        """
        async with self._uow_factory(owner) as uow:
            sitting = await self._require_sitting(uow, sitting_id)
            sitting_events = await uow.review_events.list_by_sitting(sitting_id)
            by_id = await self._reviewable_by_id(owner)
            present = sitting.visible(frozenset(by_id))
            reviewed_at = self._clock.now()
            sitting.guard_outcome(card_id, present, sitting_events, reviewed_at)
            event = ReviewEvent(
                card_id=card_id,
                reviewed_at=reviewed_at,
                payload=Graded(grade=grade),
                sitting_id=sitting_id,
            )
            previous = await self._previous_state(uow, card_id)
            next_state = self._scheduler.review(previous, card_id, grade, reviewed_at)
            states = await uow.scheduling_states.get_many(tuple(by_id))
            updated_states = dict(states)
            updated_states[card_id] = next_state
            events_after = (*sitting_events, event)
            due = DuePartitionDTO.from_domain(
                partition_due(
                    frozenset(by_id),
                    updated_states,
                    sitting,
                    events_after,
                    reviewed_at,
                    self._scheduler.stamp(),
                )
            )
            result = self._applied_dto(
                sitting,
                sitting_id,
                present,
                events_after,
                by_id,
                due,
            )

            await uow.review_events.save(event)
            await uow.scheduling_states.save(next_state)
            await uow.commit()

        return result

    async def _require_sitting(self, uow: UnitOfWork, sitting_id: SittingId) -> Sitting:
        sitting = await uow.sittings.get(sitting_id)
        if sitting is None:
            raise SittingNotFoundError
        return sitting

    async def _reviewable_by_id(self, owner: UserId) -> dict[CardId, ReviewableCard]:
        reviewable = await self._catalog.list_reviewable(owner)
        return {card.id: card for card in reviewable}

    async def _previous_state(
        self, uow: UnitOfWork, card_id: CardId
    ) -> SchedulingState | None:
        memoized = await uow.scheduling_states.get(card_id)
        if memoized is not None and memoized.stamp == self._scheduler.stamp():
            return memoized
        prior_events = await uow.review_events.list_by_card(card_id)
        return SchedulingReplay(self._scheduler).replay(card_id, prior_events)

    def _applied_dto(
        self,
        sitting: Sitting,
        sitting_id: SittingId,
        present: frozenset[CardId],
        events_after: Sequence[ReviewEvent],
        by_id: Mapping[CardId, ReviewableCard],
        due: DuePartitionDTO,
    ) -> GradeAppliedDTO:
        outstanding_count = len(sitting.outstanding(present, events_after))
        if sitting.is_finished(present, events_after):
            return GradeAppliedDTO(
                sitting_id=sitting_id.value,
                sitting_complete=True,
                outstanding_count=outstanding_count,
                next_card_id=None,
                next_front=None,
                due=due,
            )
        next_card_id = sitting.next_card(present, events_after)
        assert next_card_id is not None
        next_card = by_id[next_card_id]
        return GradeAppliedDTO(
            sitting_id=sitting_id.value,
            sitting_complete=False,
            outstanding_count=outstanding_count,
            next_card_id=next_card_id.value,
            next_front=next_card.front,
            due=due,
        )
