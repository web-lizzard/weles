from collections.abc import Sequence
from typing import Literal, override

from domain.capture.deps import CaptureDeps
from domain.capture.turn import (
    AssistantMessageRecorded,
    CaptureEvent,
    CaptureTurn,
    ConversationRequested,
    DraftingConsentSignalled,
    SessionTopicProposed,
    UserMessageRecorded,
)
from domain.capture.value_objects import (
    CapturePhase,
    ConversationRequest,
    DraftingConsent,
    Label,
    NoteContent,
    SessionTopic,
)
from domain.shared.graph.machine import StateMachine
from domain.shared.graph.model import (
    Action,
    Graph,
    State,
    Tool,
    ToolArguments,
    ToolResult,
    Transition,
)


class CaptureMachine(
    StateMachine[CaptureTurn, CaptureDeps, CaptureEvent, CapturePhase]
):
    """Capture's phase graph, bound to the capture session.

    The first concrete composition of `domain/shared/graph/`. It supplies the
    graph and the two aggregate hooks and nothing else — every other behaviour
    is inherited mechanics.
    """

    @property
    @override
    def graph(self) -> Graph[CaptureTurn, CaptureDeps, CaptureEvent, CapturePhase]:
        return _CAPTURE_GRAPH

    @override
    def state_name_of(self, context: CaptureTurn) -> CapturePhase:
        return context.session.phase

    @override
    def enter_state(self, context: CaptureTurn, name: CapturePhase) -> None:
        context.session.enter_phase(name)


class Conversing(State[CaptureTurn, CaptureDeps, CaptureEvent]):
    """Talking the topic through. The session sits here for many turns, and its
    tool set narrows as the turns do their work."""

    @property
    @override
    def description(self) -> str:
        return "Talk through the session topic with the user."

    @property
    @override
    def tools(self) -> Sequence[Tool[CaptureTurn, ToolResult]]:
        return (_ASSESS_COVERAGE, _PROPOSE_SESSION_TOPIC, _SIGNAL_DRAFTING_CONSENT)

    @property
    @override
    def actions(self) -> Sequence[Action[CaptureTurn, CaptureDeps, CaptureEvent]]:
        return (
            _assign_session_topic,
            _record_drafting_consent,
            _record_user_message,
            _record_assistant_message,
        )

    @override
    def get_tools(
        self, context: CaptureTurn
    ) -> Sequence[Tool[CaptureTurn, ToolResult]]:
        """Naming the session's topic is offered only until it has one — the
        filter `send_message.py:83` performs today as `if session.topic is
        None`, moved off the command and onto the phase that owns it."""
        if context.session.topic is not None:
            return (_ASSESS_COVERAGE, _SIGNAL_DRAFTING_CONSENT)
        return self.tools

    @override
    def get_actions(
        self, context: CaptureTurn, event: CaptureEvent
    ) -> Sequence[Action[CaptureTurn, CaptureDeps, CaptureEvent]]:
        """Assigning the session topic runs on a `SessionTopicProposed` and on
        nothing else; recording consent runs only on `DraftingConsentSignalled`.
        A recorded message is appended in either phase."""
        _ = context
        selected: list[Action[CaptureTurn, CaptureDeps, CaptureEvent]] = []
        if isinstance(event, SessionTopicProposed):
            selected.append(_assign_session_topic)
        if isinstance(event, DraftingConsentSignalled):
            selected.append(_record_drafting_consent)
        selected.extend(_message_recording_actions(event))
        return tuple(selected)


class Drafting(State[CaptureTurn, CaptureDeps, CaptureEvent]):
    """Writing the note. Every tool here proposes a part of it; assembling and
    persisting the note stays with the command."""

    @property
    @override
    def description(self) -> str:
        return "Draft the note from what the session captured."

    @property
    @override
    def tools(self) -> Sequence[Tool[CaptureTurn, ToolResult]]:
        return (
            _PROPOSE_NOTE_TOPIC,
            _PROPOSE_NOTE_TAG,
            _PROPOSE_NOTE_CONTENT,
            _REQUEST_CONVERSATION,
        )

    @property
    @override
    def actions(self) -> Sequence[Action[CaptureTurn, CaptureDeps, CaptureEvent]]:
        return (
            _record_conversation_request,
            _record_user_message,
            _record_assistant_message,
        )

    @override
    def get_actions(
        self, context: CaptureTurn, event: CaptureEvent
    ) -> Sequence[Action[CaptureTurn, CaptureDeps, CaptureEvent]]:
        _ = context
        selected: list[Action[CaptureTurn, CaptureDeps, CaptureEvent]] = []
        if isinstance(event, ConversationRequested):
            selected.append(_record_conversation_request)
        selected.extend(_message_recording_actions(event))
        return tuple(selected)


class CoverageAssessed(ToolResult, frozen=True):
    """How sure of the topic the user seems. Shapes what the agent says and
    gates nothing — no guard reads it at any value, including 1.0 (FR-03)."""

    tool: Literal["assess_coverage"] = "assess_coverage"
    coverage: float


class SessionTopicProposal(ToolResult, frozen=True):
    tool: Literal["propose_session_topic"] = "propose_session_topic"
    topic: SessionTopic


class NoteTopicProposal(ToolResult, frozen=True):
    tool: Literal["propose_note_topic"] = "propose_note_topic"
    label: Label


class NoteTagProposal(ToolResult, frozen=True):
    tool: Literal["propose_note_tag"] = "propose_note_tag"
    label: Label


class NoteContentProposal(ToolResult, frozen=True):
    tool: Literal["propose_note_content"] = "propose_note_content"
    content: NoteContent


class DraftingConsentSignal(ToolResult, frozen=True):
    tool: Literal["signal_drafting_consent"] = "signal_drafting_consent"


class ConversationRequestSignal(ToolResult, frozen=True):
    tool: Literal["request_conversation"] = "request_conversation"


def consent_given(context: CaptureTurn) -> bool:
    """The guard into drafting: the session already holds a drafting consent
    (FR-01). Messages are required when that consent is recorded, not here —
    an empty conversation cannot persist the intent in the first place.
    """
    return context.session.drafting_consent is not None


def conversation_requested(context: CaptureTurn) -> bool:
    """Whether the session holds a return-to-conversation intent (FR-02)."""
    return context.session.conversation_request is not None


def _require_str(arguments: ToolArguments, key: str) -> str:
    value = arguments[key]
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string")
    return value


def _require_float(arguments: ToolArguments, key: str) -> float:
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{key} must be a number")
    return float(value)


async def _assess_coverage(
    context: CaptureTurn, arguments: ToolArguments
) -> CoverageAssessed:
    _ = context
    return CoverageAssessed(coverage=_require_float(arguments, "coverage"))


async def _propose_session_topic(
    context: CaptureTurn, arguments: ToolArguments
) -> SessionTopicProposal:
    _ = context
    return SessionTopicProposal(
        topic=SessionTopic(value=_require_str(arguments, "topic"))
    )


async def _propose_note_topic(
    context: CaptureTurn, arguments: ToolArguments
) -> NoteTopicProposal:
    _ = context
    return NoteTopicProposal(label=Label(value=_require_str(arguments, "label")))


async def _propose_note_tag(
    context: CaptureTurn, arguments: ToolArguments
) -> NoteTagProposal:
    _ = context
    return NoteTagProposal(label=Label(value=_require_str(arguments, "label")))


async def _propose_note_content(
    context: CaptureTurn, arguments: ToolArguments
) -> NoteContentProposal:
    _ = context
    return NoteContentProposal(
        content=NoteContent(value=_require_str(arguments, "content"))
    )


async def _signal_drafting_consent(
    context: CaptureTurn, arguments: ToolArguments
) -> DraftingConsentSignal:
    _ = context, arguments
    return DraftingConsentSignal()


async def _request_conversation(
    context: CaptureTurn, arguments: ToolArguments
) -> ConversationRequestSignal:
    _ = context, arguments
    return ConversationRequestSignal()


async def _assign_session_topic(
    context: CaptureTurn, _deps: CaptureDeps, event: CaptureEvent
) -> None:
    """Put the proposed topic on the session, in memory. `assign_topic` refuses
    a second assignment, which is why `Conversing` withdraws the tool once the
    session has one."""
    if isinstance(event, SessionTopicProposed):
        context.session.assign_topic(event.topic)


async def _record_drafting_consent(
    context: CaptureTurn, _deps: CaptureDeps, event: CaptureEvent
) -> None:
    _ = event
    if context.messages:
        context.session.record_drafting_consent(DraftingConsent())


async def _record_conversation_request(
    context: CaptureTurn, _deps: CaptureDeps, event: CaptureEvent
) -> None:
    _ = event
    context.session.record_conversation_request(ConversationRequest())


async def _consume_drafting_consent(context: CaptureTurn, _deps: CaptureDeps) -> None:
    context.session.clear_drafting_consent()


async def _consume_conversation_request(
    context: CaptureTurn, _deps: CaptureDeps
) -> None:
    context.session.clear_conversation_request()


def _message_recording_actions(
    event: CaptureEvent,
) -> Sequence[Action[CaptureTurn, CaptureDeps, CaptureEvent]]:
    if isinstance(event, UserMessageRecorded):
        return (_record_user_message,)
    if isinstance(event, AssistantMessageRecorded):
        return (_record_assistant_message,)
    return ()


async def _record_user_message(
    context: CaptureTurn, _deps: CaptureDeps, event: CaptureEvent
) -> None:
    if isinstance(event, UserMessageRecorded):
        context.record_message(event.message)


async def _record_assistant_message(
    context: CaptureTurn, _deps: CaptureDeps, event: CaptureEvent
) -> None:
    if isinstance(event, AssistantMessageRecorded):
        context.record_message(event.message)


_ASSESS_COVERAGE = Tool[CaptureTurn, CoverageAssessed](
    name="assess_coverage",
    description="Judge how fully the user has covered the topic so far.",
    result=CoverageAssessed,
    handler=_assess_coverage,
)

_PROPOSE_SESSION_TOPIC = Tool[CaptureTurn, SessionTopicProposal](
    name="propose_session_topic",
    description="Name what this session is about, once it is clear.",
    result=SessionTopicProposal,
    handler=_propose_session_topic,
)

_PROPOSE_NOTE_TOPIC = Tool[CaptureTurn, NoteTopicProposal](
    name="propose_note_topic",
    description="Propose a topic label for the note being drafted.",
    result=NoteTopicProposal,
    handler=_propose_note_topic,
)

_PROPOSE_NOTE_TAG = Tool[CaptureTurn, NoteTagProposal](
    name="propose_note_tag",
    description="Propose a tag label for the note being drafted.",
    result=NoteTagProposal,
    handler=_propose_note_tag,
)

_PROPOSE_NOTE_CONTENT = Tool[CaptureTurn, NoteContentProposal](
    name="propose_note_content",
    description="Write the body of the note being drafted.",
    result=NoteContentProposal,
    handler=_propose_note_content,
)

_SIGNAL_DRAFTING_CONSENT = Tool[CaptureTurn, DraftingConsentSignal](
    name="signal_drafting_consent",
    description="Read the user's latest message as consent to start drafting.",
    result=DraftingConsentSignal,
    handler=_signal_drafting_consent,
)

_REQUEST_CONVERSATION = Tool[CaptureTurn, ConversationRequestSignal](
    name="request_conversation",
    description=(
        "Read the user's latest message as a request to return to conversation."
    ),
    result=ConversationRequestSignal,
    handler=_request_conversation,
)

_CAPTURE_GRAPH = Graph[CaptureTurn, CaptureDeps, CaptureEvent, CapturePhase](
    states={
        CapturePhase.CONVERSING: Conversing(),
        CapturePhase.DRAFTING: Drafting(),
    },
    transitions={
        CapturePhase.CONVERSING: {
            CapturePhase.DRAFTING: Transition[CaptureTurn, CaptureDeps, CaptureEvent](
                guard=consent_given,
                actions=(_consume_drafting_consent,),
            )
        },
        # Guarded on purpose. Without `conversation_requested`, every drafting
        # turn would burn a segment returning to a conversation nobody asked
        # for. The consume action keeps the intent single-use so the command's
        # loop stays finite while FR-02 still forbids a terminal drafting phase.
        CapturePhase.DRAFTING: {
            CapturePhase.CONVERSING: Transition[CaptureTurn, CaptureDeps, CaptureEvent](
                guard=conversation_requested,
                actions=(_consume_conversation_request,),
            )
        },
    },
)
