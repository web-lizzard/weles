import logging
from collections.abc import Callable

from application.distill.ports import CardGeneration, UnitOfWork
from domain.distill.card_factory import CardFactory
from domain.distill.note_document import NoteDocument
from domain.distill.value_objects import (
    Anchor,
    AnchorResolution,
    CardSide,
    DistillationStatus,
    NoteId,
)
from domain.exceptions import CoreException

logger = logging.getLogger(__name__)


class GenerateCardsCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        card_generation: CardGeneration,
        card_factory: CardFactory,
    ) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory
        self._card_generation: CardGeneration = card_generation
        self._card_factory: CardFactory = card_factory

    async def handle(self, note_id: NoteId) -> None:
        async with self._uow_factory() as uow:
            note = await uow.notes.get(note_id)
            if note is None:
                logger.info("note %s not found, skipping as no-op", note_id.value)
                return
            if note.distillation_status is not DistillationStatus.GENERATING:
                logger.info("note %s redelivered, skipping as no-op", note_id.value)
                return

            try:
                proposals = await self._card_generation.generate(note.content)
            except Exception:
                logger.exception("card generation failed for note %s", note_id.value)
                note.mark_failed()
                await uow.notes.save(note)
                await uow.commit()
                return

            document = NoteDocument.of(note.content)
            for proposal in proposals:
                try:
                    front = CardSide(value=proposal.front)
                    back = CardSide(value=proposal.back)
                    anchor = Anchor(quote=proposal.quote)
                    resolution = (
                        AnchorResolution.RESOLVED
                        if document.locate(anchor) is not None
                        else AnchorResolution.UNRESOLVED
                    )
                    card = self._card_factory.mint(
                        note_id, front, back, anchor, resolution
                    )
                    await uow.cards.save(card)
                except CoreException:
                    logger.exception(
                        "skipping invalid card proposal for note %s", note_id.value
                    )
                    continue

            note.mark_ready()
            await uow.notes.save(note)
            await uow.commit()
