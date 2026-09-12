from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import Coverage, Label, NoteContent, SessionTopic


class NoteDraft(BaseModel):
    """A note under construction before it can become a domain `Note`."""

    topic: Topic | None = None
    topic_reused: bool = False
    tags: list[Tag] = Field(default_factory=list)
    tag_reused: list[bool] = Field(default_factory=list)
    content: str = ""


class CaptureTurn(BaseModel):
    """What one capture turn carries: the session, its messages, and the note
    the turn touched or created.

    This, not `CaptureSession` alone, is the machine's context. A bare session
    could not carry a note an action created in memory — it holds only a
    `NoteId` — and the command reads what a turn touched off the machine's
    state, so the note has to live here.

    `messages` is the conversation itself, not a count of it. A tool that
    reads and computes needs what was actually said: judging how far the topic
    is covered is a reading of the exchange, and a number could never support
    it. It is also what the guard into drafting checks for presence, so one
    field serves both.
    """

    session: CaptureSession
    messages: Sequence[Message]
    note: Note | None = None
    draft: NoteDraft | None = None

    def record_message(self, message: Message) -> None:
        """Append a message onto this turn's conversation in memory."""
        self.messages = (*self.messages, message)


class ReplyProduced(BaseModel, frozen=True):
    """A piece of conversational reply arrived."""

    kind: Literal["reply_produced"] = "reply_produced"
    text: str


class SessionTopicProposed(BaseModel, frozen=True):
    """The model named what the session is about."""

    kind: Literal["session_topic_proposed"] = "session_topic_proposed"
    topic: SessionTopic


class NoteTopicProposed(BaseModel, frozen=True):
    """The model proposed a topic label for the note being drafted. A label
    only — minting a `Topic` needs vocabulary the model cannot see, and stays
    with the command."""

    kind: Literal["note_topic_proposed"] = "note_topic_proposed"
    label: Label


class NoteTagProposed(BaseModel, frozen=True):
    """The model proposed a tag label for the note being drafted."""

    kind: Literal["note_tag_proposed"] = "note_tag_proposed"
    label: Label


class NoteContentProduced(BaseModel, frozen=True):
    """A piece of the note's body arrived."""

    kind: Literal["note_content_produced"] = "note_content_produced"
    content: NoteContent


class DraftingConsentSignalled(BaseModel, frozen=True):
    """The model read the user's latest message as consent to start drafting."""

    kind: Literal["drafting_consent_signalled"] = "drafting_consent_signalled"


class ConversationRequested(BaseModel, frozen=True):
    """The model read the user's latest message as a request to return to
    conversation."""

    kind: Literal["conversation_requested"] = "conversation_requested"


class CoverageAssessed(BaseModel, frozen=True):
    """The model judged how fully the session's topic has been covered."""

    kind: Literal["coverage_assessed"] = "coverage_assessed"
    coverage: Coverage


class UserMessageRecorded(BaseModel, frozen=True):
    """The command recorded the user's message onto this turn."""

    kind: Literal["user_message_recorded"] = "user_message_recorded"
    message: Message


class AssistantMessageRecorded(BaseModel, frozen=True):
    """The command recorded the assistant's message onto this turn."""

    kind: Literal["assistant_message_recorded"] = "assistant_message_recorded"
    message: Message


class DraftCompleted(BaseModel, frozen=True):
    """The command closed a drafting segment and will materialise the draft."""

    kind: Literal["draft_completed"] = "draft_completed"


type AgentEvent = Annotated[
    ReplyProduced
    | SessionTopicProposed
    | NoteTopicProposed
    | NoteTagProposed
    | NoteContentProduced
    | DraftingConsentSignalled
    | ConversationRequested
    | CoverageAssessed,
    Field(discriminator="kind"),
]
"""What a capture-agent adapter may yield.

The two message-recording events are raised by the command, not the model, so
they are not in this union: yielding one from an adapter is a type error.
"""

type CaptureEvent = (
    AgentEvent | UserMessageRecorded | AssistantMessageRecorded | DraftCompleted
)
"""What the command applies to the machine over a turn.

`AgentEvent` is everything the model produces; the two message events are
raised by the command so a turn's own exchange can reach the machine.
"""
