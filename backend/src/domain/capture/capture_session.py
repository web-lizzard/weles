from datetime import UTC, datetime

from pydantic import BaseModel

from domain.capture.exceptions import (
    CaptureSessionClosedError,
    SessionNoteAlreadyDraftedError,
    SessionNoteMissingError,
    SessionTopicAlreadyAssignedError,
)
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    CapturePhase,
    ConversationRequest,
    Coverage,
    DraftingConsent,
    NoteContent,
    NoteId,
    SessionId,
    SessionStatus,
    SessionTopic,
)
from domain.shared.identity.model import UserId


class CaptureSession(BaseModel):
    id: SessionId
    owner_id: UserId
    topic: SessionTopic | None
    note_id: NoteId | None = None
    status: SessionStatus
    phase: CapturePhase = CapturePhase.CONVERSING
    drafting_consent: DraftingConsent | None = None
    conversation_request: ConversationRequest | None = None
    assessments: tuple[Coverage, ...] = ()
    created_at: datetime

    @classmethod
    def start(cls, owner: UserId) -> "CaptureSession":
        return cls(
            id=SessionId.new(),
            owner_id=owner,
            topic=None,
            note_id=None,
            status=SessionStatus.OPEN,
            phase=CapturePhase.CONVERSING,
            created_at=datetime.now(UTC),
        )

    def enter_phase(self, phase: CapturePhase) -> None:
        """Move the session into a phase. The session is the only durable
        carrier of the phase, so this is what a transition ultimately writes."""
        if self.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError
        self.phase = phase

    def record_assessment(self, coverage: Coverage) -> None:
        """Keep a coverage assessment on the session, in order.

        Appending rather than overwriting. A single current value would be
        enough to say how covered the topic is, but not which way it moved, and
        FR-03 rests on the movement. A discarded assessment cannot be recovered
        later; a kept one can always be ignored, and `COVERAGE_TREND_WINDOW`
        is where ignoring happens.

        The session is the aggregate, so this is where the history is durable —
        the turn carries it only for the length of the turn.
        """
        self.assessments = (*self.assessments, coverage)

    def record_drafting_consent(self, consent: DraftingConsent) -> None:
        self.drafting_consent = consent

    def record_conversation_request(self, request: ConversationRequest) -> None:
        self.conversation_request = request

    def clear_drafting_consent(self) -> None:
        self.drafting_consent = None

    def clear_conversation_request(self) -> None:
        self.conversation_request = None

    def assign_topic(self, topic: SessionTopic) -> None:
        if self.topic is not None:
            raise SessionTopicAlreadyAssignedError
        self.topic = topic

    def draft_note(
        self,
        topic: Topic,
        content: NoteContent,
        tags: list[Tag],
    ) -> Note:
        if self.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError
        if self.note_id is not None:
            raise SessionNoteAlreadyDraftedError
        note = Note.draft(self.owner_id, self.id, topic, content, tags)
        self.note_id = note.id
        return note

    def approve(self, note: Note) -> None:
        if self.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError
        if self.note_id is None or self.note_id != note.id:
            raise SessionNoteMissingError
        note.approve(self.id)
        self._close()

    def _close(self) -> None:
        if self.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError
        self.status = SessionStatus.CLOSED
