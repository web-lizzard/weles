# pyright: reportUnusedParameter=false
from adapters.out.sqlalchemy.remember.models import (
    RememberReviewEventRow,
    RememberSchedulingStateRow,
    RememberSittingRow,
)
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting


def sitting_to_row(sitting: Sitting) -> RememberSittingRow:
    raise NotImplementedError


def sitting_to_domain(row: RememberSittingRow) -> Sitting:
    raise NotImplementedError


def review_event_to_row(event: ReviewEvent) -> RememberReviewEventRow:
    raise NotImplementedError


def review_event_to_domain(row: RememberReviewEventRow) -> ReviewEvent:
    raise NotImplementedError


def scheduling_state_to_row(state: SchedulingState) -> RememberSchedulingStateRow:
    raise NotImplementedError


def scheduling_state_to_domain(row: RememberSchedulingStateRow) -> SchedulingState:
    raise NotImplementedError
