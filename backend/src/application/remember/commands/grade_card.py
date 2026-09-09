# pyright: reportUnusedParameter=false
from collections.abc import Callable

from application.remember.dto import GradeAppliedDTO
from application.remember.ports import Clock, UnitOfWork
from domain.remember.ports import ReviewCatalog, Scheduler
from domain.remember.value_objects import CardId, Grade, SittingId


class GradeCardCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        catalog: ReviewCatalog,
        scheduler: Scheduler,
        clock: Clock,
    ) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory
        self._catalog: ReviewCatalog = catalog
        self._scheduler: Scheduler = scheduler
        self._clock: Clock = clock

    async def handle(
        self, sitting_id: SittingId, card_id: CardId, grade: Grade
    ) -> GradeAppliedDTO:
        """
        1. Load sitting or SittingNotFoundError. Load events.
           present = sitting.visible(live).
        2. Guard: sitting.contains(card_id) else CardNotInSittingError.
        3. Guard: not sitting.is_finished(...) else SittingAlreadyCompleteError.
        4. Guard: card_id == sitting.next_card(...) else CardNotPresentableError
           (discarded, already finished, not least-shown, or not the seeded pick).
        5. reviewed_at = clock.now() once. Build ReviewEvent with that instant.
        6. previous = memoized state if stamp matches scheduler.stamp();
           else SchedulingReplay.replay(card events excluding this one).
        7. next_state = scheduler.review(previous, card_id, grade, reviewed_at).
        8. One UoW: save event first, then scheduling state; commit.
           Event is the write that must not be lost.
        9. Recompute pool; if sitting.is_finished, return complete with no next card.
           Else sitting.next_card(...) and return its front.
        ShowingLimit comes from the sitting, not compose.
        Scheduler.review must not receive sitting_id.
        Replay reads only card_id, reviewed_at, grade.
        """
        ...
