from application.distill.queries.list_cards_for_note import (
    AnchorLocationDTO,
    CardListItemDTO,
)
from domain.distill.exceptions import DistillNoteNotFoundError
from domain.distill.note_document import AnchorLocation, NoteDocument
from domain.distill.ports import CardRepository, NoteRepository
from domain.distill.value_objects import NoteId
from domain.shared.identity.model import UserId


class InMemoryListCardsForNoteQueryAdapter:
    def __init__(
        self, note_repository: NoteRepository, card_repository: CardRepository
    ) -> None:
        self._note_repository: NoteRepository = note_repository
        self._card_repository: CardRepository = card_repository

    async def list_cards_for_note(
        self, owner: UserId, note_id: NoteId
    ) -> list[CardListItemDTO]:
        _ = owner
        note = await self._note_repository.get(note_id)
        if note is None:
            raise DistillNoteNotFoundError
        live_cards = [
            card
            for card in await self._card_repository.list_by_note(note_id)
            if card.discard is None
        ]
        live_cards.sort(key=lambda card: card.created_at)
        document = NoteDocument.of(note.content)
        return [
            CardListItemDTO(
                card_id=card.id.value,
                front=card.front.value,
                back=card.back.value,
                anchor_quote=card.anchor.quote,
                anchor_location=_to_anchor_location_dto(document.locate(card.anchor)),
                created_at=card.created_at,
            )
            for card in live_cards
        ]


def _to_anchor_location_dto(
    location: AnchorLocation | None,
) -> AnchorLocationDTO | None:
    if location is None:
        return None
    return AnchorLocationDTO(
        block_index=location.block_index,
        start=location.start,
        end=location.end,
        precision=location.precision.value,
    )
