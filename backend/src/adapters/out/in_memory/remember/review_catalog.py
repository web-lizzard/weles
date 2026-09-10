# pyright: reportUnusedParameter=false
from collections.abc import Sequence

from domain.distill.ports import CardRepository, NoteRepository
from domain.remember.ports import ReviewableCard
from domain.remember.value_objects import CardId


class InMemoryReviewCatalog:
    def __init__(
        self, note_repository: NoteRepository, card_repository: CardRepository
    ) -> None: ...

    async def list_reviewable(self) -> Sequence[ReviewableCard]: ...

    async def get_reviewable(self, card_id: CardId) -> ReviewableCard | None: ...
