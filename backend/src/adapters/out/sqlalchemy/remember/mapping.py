from adapters.out.sqlalchemy.remember.models import (
    RememberReviewEventRow,
    RememberSchedulingStateRow,
    RememberSittingCardRow,
    RememberSittingRow,
)
from domain.remember.review_event import ReviewEvent
from domain.remember.scheduling_state import SchedulingState
from domain.remember.sitting import Sitting
from domain.remember.value_objects import (
    Grade,
    Graded,
    Rejection,
    Reveal,
    ReviewEventPayload,
    SchedulerStamp,
)
from domain.shared.identity.model import UserId


def sitting_to_row(sitting: Sitting) -> RememberSittingRow:
    return RememberSittingRow(
        id=sitting.id,
        owner_id=sitting.owner_id.value,
        opened_at=sitting.opened_at,
        showing_limit=sitting.showing_limit,
        resume_horizon=sitting.resume_horizon,
        cards=[
            RememberSittingCardRow(sitting_id=sitting.id, card_id=card_id)
            for card_id in sitting.card_ids
        ],
    )


def sitting_to_domain(row: RememberSittingRow) -> Sitting:
    return Sitting(
        id=row.id,
        owner_id=UserId(value=row.owner_id),
        card_ids=frozenset(card.card_id for card in row.cards),
        opened_at=row.opened_at,
        showing_limit=row.showing_limit,
        resume_horizon=row.resume_horizon,
    )


def _payload_from_row(row: RememberReviewEventRow) -> ReviewEventPayload:
    if row.kind == "graded":
        if row.grade is None:
            raise ValueError("graded review event row missing grade")
        return Graded(grade=Grade(row.grade))
    if row.kind == "rejected":
        return Rejection()
    if row.kind == "revealed":
        return Reveal()
    raise ValueError(f"unknown review event kind: {row.kind}")


def review_event_to_row(event: ReviewEvent) -> RememberReviewEventRow:
    payload = event.payload
    if isinstance(payload, Graded):
        return RememberReviewEventRow(
            sitting_id=event.sitting_id,
            card_id=event.card_id,
            reviewed_at=event.reviewed_at,
            kind="graded",
            grade=payload.grade.value,
        )
    if isinstance(payload, Rejection):
        return RememberReviewEventRow(
            sitting_id=event.sitting_id,
            card_id=event.card_id,
            reviewed_at=event.reviewed_at,
            kind="rejected",
            grade=None,
        )
    return RememberReviewEventRow(
        sitting_id=event.sitting_id,
        card_id=event.card_id,
        reviewed_at=event.reviewed_at,
        kind="revealed",
        grade=None,
    )


def review_event_to_domain(row: RememberReviewEventRow) -> ReviewEvent:
    return ReviewEvent(
        card_id=row.card_id,
        sitting_id=row.sitting_id,
        reviewed_at=row.reviewed_at,
        payload=_payload_from_row(row),
    )


def scheduling_state_to_row(state: SchedulingState) -> RememberSchedulingStateRow:
    return RememberSchedulingStateRow(
        card_id=state.card_id,
        due_at=state.due_at,
        scheduler_state=state.scheduler_state,
        stamp_algorithm=state.stamp.algorithm,
        stamp_parameter_version=state.stamp.parameter_version,
    )


def scheduling_state_to_domain(row: RememberSchedulingStateRow) -> SchedulingState:
    return SchedulingState(
        card_id=row.card_id,
        due_at=row.due_at,
        scheduler_state=row.scheduler_state,
        stamp=SchedulerStamp(
            algorithm=row.stamp_algorithm,
            parameter_version=row.stamp_parameter_version,
        ),
    )
