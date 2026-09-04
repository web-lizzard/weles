from collections.abc import Callable
from datetime import datetime

from application.distill.ports import UnitOfWork
from domain.distill.value_objects import (
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)


class SaveNoteCommand:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory: Callable[[], UnitOfWork] = uow_factory

    async def handle(
        self,
        _note_id: NoteId,
        _session_id: SessionId,
        _topic: TopicSnapshot,
        _content: NoteContent,
        _tags: list[TagSnapshot],
        _approved_at: datetime,
    ) -> None:
        raise NotImplementedError
