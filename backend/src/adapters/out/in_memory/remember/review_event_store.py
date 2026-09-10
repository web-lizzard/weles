from collections.abc import Iterable, Sequence

from domain.remember.review_event import ReviewEvent
from domain.remember.value_objects import CardId, SittingId


class InMemoryReviewEventStore:
    def __init__(self) -> None:
        self._events: list[ReviewEvent] = []

    async def save(self, event: ReviewEvent) -> None:
        self._events.append(event)

    async def list_by_card(self, card_id: CardId) -> Sequence[ReviewEvent]:
        return self._chronological(
            event for event in self._events if event.card_id == card_id
        )

    async def list_by_sitting(self, sitting_id: SittingId) -> Sequence[ReviewEvent]:
        return self._chronological(
            event for event in self._events if event.sitting_id == sitting_id
        )

    def snapshot(self) -> list[ReviewEvent]:
        return list(self._events)

    def restore(self, snapshot: list[ReviewEvent]) -> None:
        self._events = list(snapshot)

    @staticmethod
    def _chronological(events: Iterable[ReviewEvent]) -> list[ReviewEvent]:
        return sorted(events, key=lambda event: event.reviewed_at)
