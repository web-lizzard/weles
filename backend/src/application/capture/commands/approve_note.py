from application.capture.dto import ApproveNoteResponseDTO
from application.capture.ports import UnitOfWork
from domain.capture.exceptions import (
    CaptureSessionNotFoundError,
    NoteNotFoundError,
    SessionNoteMissingError,
)
from domain.capture.outbox import NoteApprovedPayload
from domain.capture.value_objects import SessionId
from domain.shared.identity.model import UserId


class ApproveNoteCommand:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow: UnitOfWork = uow

    async def handle(
        self, owner: UserId, session_id: SessionId
    ) -> ApproveNoteResponseDTO:
        _ = owner
        async with self._uow as uow:
            session = await uow.capture_sessions.get(session_id)
            if session is None:
                raise CaptureSessionNotFoundError
            if session.note_id is None:
                raise SessionNoteMissingError

            note = await uow.notes.get(session.note_id)
            if note is None:
                raise NoteNotFoundError

            session.approve(note)
            await uow.notes.add(note)
            await uow.capture_sessions.save(session)

            vocabulary = await uow.note_vocabulary.resolve(note)

            payload = NoteApprovedPayload.of(note, vocabulary.topic, vocabulary.tags)
            await uow.outbox.append(payload.to_envelope())

            response = ApproveNoteResponseDTO(
                note_id=payload.note_id,
                topic=payload.topic.label,
                tags=[tag.label for tag in payload.tags],
                approved_at=payload.approved_at,
            )

            await uow.commit()

        return response
