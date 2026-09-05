from collections.abc import Callable

from application.distill.ports import CardGeneration, NoteDocumentParser, UnitOfWork
from domain.distill.card_factory import CardFactory
from domain.distill.value_objects import NoteId


class GenerateCardsCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        card_generation: CardGeneration,
        parser: NoteDocumentParser,
        card_factory: CardFactory,
    ) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory
        self._card_generation: CardGeneration = card_generation
        self._parser: NoteDocumentParser = parser
        self._card_factory: CardFactory = card_factory

    async def handle(self, _note_id: NoteId) -> None: ...
