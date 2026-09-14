from application.remember.dto import CardSourceDTO, SourceBlockDTO, SourceSpanDTO
from application.remember.ports import Clock
from domain.remember.exceptions import (
    CardNotInSittingError,
    SittingExpiredError,
    SittingNotFoundError,
    SourceNotAvailableError,
)
from domain.remember.ports import (
    CardSourceLocator,
    ReviewEventReader,
    SittingReader,
)
from domain.remember.value_objects import CardId, Reveal, SittingId
from domain.shared.identity.model import UserId


class CardSourceQuery:
    def __init__(
        self,
        sittings: SittingReader,
        events: ReviewEventReader,
        locator: CardSourceLocator,
        clock: Clock,
    ) -> None:
        self._sittings: SittingReader = sittings
        self._events: ReviewEventReader = events
        self._locator: CardSourceLocator = locator
        self._clock: Clock = clock

    async def handle(
        self, owner: UserId, sitting_id: SittingId, card_id: CardId
    ) -> CardSourceDTO:
        """Return blocks and span when the back was revealed and source resolves."""
        sitting = await self._sittings.get(sitting_id)
        if sitting is None or sitting.owner_id != owner:
            raise SittingNotFoundError
        if not sitting.is_offered(self._clock.now()):
            raise SittingExpiredError
        if not sitting.contains(card_id):
            raise CardNotInSittingError

        sitting_events = await self._events.list_by_sitting(sitting_id)
        revealed = any(
            event.card_id == card_id and isinstance(event.payload, Reveal)
            for event in sitting_events
        )
        if not revealed:
            raise SourceNotAvailableError

        located = await self._locator.locate(owner, card_id)
        if located is None:
            raise SourceNotAvailableError

        return CardSourceDTO(
            blocks=[
                SourceBlockDTO(index=block.index, text=block.text)
                for block in located.blocks
            ],
            span=SourceSpanDTO(
                block_index=located.span.block_index,
                start=located.span.start,
                end=located.span.end,
            ),
        )
