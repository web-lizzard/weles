from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from domain.capture.capture_session import CaptureSession
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.value_objects import Label, NoteContent, SessionTopic


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


class TurnOpened(BaseModel, frozen=True):
    """The start of a turn, before the model is called. Carries whether the
    user's latest message was read as consent to start drafting — a reading the
    model makes and never generates on its own (FR-01)."""

    kind: Literal["turn_opened"] = "turn_opened"
    consent_signalled: bool


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


type CaptureEvent = Annotated[
    TurnOpened
    | ReplyProduced
    | SessionTopicProposed
    | NoteTopicProposed
    | NoteTagProposed
    | NoteContentProduced,
    Field(discriminator="kind"),
]
"""What the command applies to the machine over a turn.

Domain vocabulary, and the domain's own: `CaptureAgentPort` both takes and
yields these, so nothing from the adapter's world crosses the seam.

A discriminated union rather than an envelope with a payload. The payloads do
differ, but these events never leave the process — adapter to command to
machine, all inside one turn — so the union carries full types the whole way
and a guard or action narrows on `isinstance` with the fields already known.
An envelope is what `OutboxEnvelope` is for: a `dict[str, object]` payload,
opaque because it has to survive serialization to another process. Paying that
price here would buy nothing and lose the narrowing.
"""
