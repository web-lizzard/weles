"""Stateless domain operations on review event payloads.

These are domain services in the DDD sense: behaviour that does not belong on a
single value object or aggregate, but stays free of ports and infrastructure.
"""

from domain.remember.value_objects import (
    Grade,
    Graded,
    Rejection,
    ReviewEventPayload,
)


def is_accounting(payload: ReviewEventPayload) -> bool:
    return isinstance(payload, (Graded, Rejection))


def is_finishing(payload: ReviewEventPayload) -> bool:
    if isinstance(payload, Graded):
        return payload.grade in (Grade.GOOD, Grade.EASY)
    if isinstance(payload, Rejection):
        return True
    return False
