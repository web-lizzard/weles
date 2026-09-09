# pyright: reportUnusedParameter=false
from application.remember.dto import RevealedCardDTO
from domain.remember.ports import ReviewCatalog, SittingRepository
from domain.remember.value_objects import CardId, SittingId


class RevealBackQuery:
    def __init__(
        self,
        sittings: SittingRepository,
        catalog: ReviewCatalog,
    ) -> None:
        self._sittings: SittingRepository = sittings
        self._catalog: ReviewCatalog = catalog

    async def handle(self, sitting_id: SittingId, card_id: CardId) -> RevealedCardDTO:
        """
        No UnitOfWork. Sitting exists; card is a member; catalog still
        has it. Return front and back. Does not write.
        Does not re-derive the card in front — that is CurrentCardQuery.
        SittingNotFoundError / CardNotInSittingError / CardNotReviewableError.
        """
        ...
