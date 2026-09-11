from domain.distill.note_document import NoteDocument
from domain.distill.ports import CardRepository, NoteRepository
from domain.distill.value_objects import CardId as DistillCardId
from domain.remember.ports import CardSource, SourceBlock, SourceSpan
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
        card = await self._cards.get(DistillCardId(value=card_id.value))
        if card is None or card.discard is not None:
            return None
        note = await self._notes.get(card.note_id)
        if note is None:
            return None
        document = NoteDocument.of(note.content)
        location = document.locate(card.anchor)
        if location is None:
            return None
        return CardSource(
            blocks=[
                SourceBlock(index=block.index, text=block.text)
                for block in document.blocks
            ],
            span=SourceSpan(
                block_index=location.block_index,
                start=location.start,
                end=location.end,
            ),
        )
