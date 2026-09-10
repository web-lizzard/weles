# pyright: reportUnusedParameter=false
from datetime import datetime

from domain.remember.scheduling_state import SchedulingState
from domain.remember.value_objects import CardId, Grade, SchedulerStamp


class FsrsScheduler:
    def stamp(self) -> SchedulerStamp: ...

    def review(
        self,
        previous: SchedulingState | None,
        card_id: CardId,
        grade: Grade,
        reviewed_at: datetime,
    ) -> SchedulingState: ...
