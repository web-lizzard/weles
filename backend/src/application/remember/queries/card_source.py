from application.remember.dto import CardSourceDTO
from application.remember.ports import Clock
from domain.remember.ports import CardSourceLocator, ReviewEventStore, SittingRepository
from domain.remember.value_objects import CardId, SittingId


class CardSourceQuery:
    def __init__(
        self,
        sittings: SittingRepository,
        events: ReviewEventStore,
        locator: CardSourceLocator,
        clock: Clock,
    ) -> None:
        self._sittings: SittingRepository = sittings
        self._events: ReviewEventStore = events
        self._locator: CardSourceLocator = locator
        self._clock: Clock = clock

    async def handle(self, sitting_id: SittingId, card_id: CardId) -> CardSourceDTO:
        """Return blocks and span when the back was revealed and source resolves."""
        _ = (sitting_id, card_id)
        raise NotImplementedError
