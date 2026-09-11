from domain.distill.ports import CardRepository, NoteRepository
from domain.remember.ports import CardSource
from domain.remember.value_objects import CardId


class InMemoryCardSourceLocator:
    """The second place a distill note is read from remember.

    Resolution maps a card's anchor quote onto note blocks; distill's
    repositories are the source of truth and never leak past this adapter.
    """

    def __init__(
        self, note_repository: NoteRepository, card_repository: CardRepository
    ) -> None:
        self._notes: NoteRepository = note_repository
        self._cards: CardRepository = card_repository

    async def locate(self, card_id: CardId) -> CardSource | None:
        _ = card_id
        raise NotImplementedError
