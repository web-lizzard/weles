import logging
from collections.abc import Callable
from datetime import datetime

from application.distill.ports import UnitOfWork
from domain.distill.note import mint_note
from domain.distill.outbox import NoteSavedPayload
from domain.distill.value_objects import (
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)

logger = logging.getLogger(__name__)


class SaveNoteCommand:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory

    async def handle(
        self,
        note_id: NoteId,
        session_id: SessionId,
        topic: TopicSnapshot,
        content: NoteContent,
        tags: list[TagSnapshot],
        approved_at: datetime,
    ) -> None:
        async with self._uow_factory() as uow:
            existing = await uow.notes.get(note_id)
            if existing is not None:
                logger.info("note %s redelivered, skipping as no-op", note_id.value)
                return

            note = mint_note(note_id, session_id, topic, content, tags, approved_at)
            await uow.notes.add(note)
            payload = NoteSavedPayload(note_id=note_id.value)
            await uow.outbox.append(payload.to_envelope())
            await uow.commit()
