from application.distill.queries.list_notes import NoteListItemDTO
from domain.distill.ports import CardRepository, NoteRepository


class InMemoryListNotesQueryAdapter:
    def __init__(
        self, note_repository: NoteRepository, card_repository: CardRepository
    ) -> None:
        self._note_repository: NoteRepository = note_repository
        self._card_repository: CardRepository = card_repository

    async def list_notes(self) -> list[NoteListItemDTO]:
        items: list[NoteListItemDTO] = []
        for note in await self._note_repository.list_all():
            live_cards = [
                card
                for card in await self._card_repository.list_by_note(note.id)
                if card.discard is None
            ]
            last_updated_at = max(
                note.updated_at,
                max((card.created_at for card in live_cards), default=note.updated_at),
            )
            items.append(
                NoteListItemDTO(
                    note_id=note.id.value,
                    topic_label=note.topic.label,
                    distillation_status=note.distillation_status,
                    card_count=len(live_cards),
                    last_updated_at=last_updated_at,
                )
            )
        items.sort(key=lambda item: item.last_updated_at, reverse=True)
        return items
