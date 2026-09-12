# Blocking comment. Present only while the handler, guard and action bodies
# below are absent — each reads its parameters nowhere in a `...` body. Remove
# it once the bodies land.
# pyright: reportUnusedParameter=false
from collections.abc import Sequence
from typing import Literal, override

from domain.capture.turn import CaptureEvent, CaptureTurn
from domain.capture.value_objects import CapturePhase, Label, NoteContent, SessionTopic
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


class CaptureMachine(StateMachine[CaptureTurn, CaptureEvent, CapturePhase]):
    """Capture's phase graph, bound to the capture session.

    The first concrete composition of `domain/shared/graph/`. It supplies the
    graph and the two aggregate hooks and nothing else — every other behaviour
    is inherited mechanics.
    """

    @property
    @override
    def graph(self) -> Graph[CaptureTurn, CaptureEvent, CapturePhase]:
        return _CAPTURE_GRAPH

    @override
    def state_name_of(self, context: CaptureTurn) -> CapturePhase:
        return context.session.phase

    @override
    def enter_state(self, context: CaptureTurn, name: CapturePhase) -> None:
        context.session.enter_phase(name)


class Conversing(State[CaptureTurn, CaptureEvent]):
    """Talking the topic through. The session sits here for many turns, and its
    tool set narrows as the turns do their work."""

    @property
    @override
    def description(self) -> str:
        return "Talk through the session topic with the user."

    @property
    @override
    def tools(self) -> Sequence[Tool[CaptureTurn, ToolResult]]:
        return (_ASSESS_COVERAGE, _PROPOSE_SESSION_TOPIC)

    @property
    @override
    def actions(self) -> Sequence[Action[CaptureTurn, CaptureEvent]]:
        return (_assign_session_topic,)

    @override
    def get_tools(
        self, context: CaptureTurn
    ) -> Sequence[Tool[CaptureTurn, ToolResult]]:
        """Naming the session's topic is offered only until it has one — the
        filter `send_message.py:83` performs today as `if session.topic is
        None`, moved off the command and onto the phase that owns it."""
        ...

    @override
    def get_actions(
        self, context: CaptureTurn, event: CaptureEvent
    ) -> Sequence[Action[CaptureTurn, CaptureEvent]]:
        """Assigning the session topic runs on a `SessionTopicProposed` and on
        nothing else."""
        ...


class Drafting(State[CaptureTurn, CaptureEvent]):
    """Writing the note. Every tool here proposes a part of it; assembling and
    persisting the note stays with the command."""

    @property
    @override
    def description(self) -> str:
        return "Draft the note from what the session captured."

    @property
    @override
    def tools(self) -> Sequence[Tool[CaptureTurn, ToolResult]]:
        return (_PROPOSE_NOTE_TOPIC, _PROPOSE_NOTE_TAG, _PROPOSE_NOTE_CONTENT)

    @property
    @override
    def actions(self) -> Sequence[Action[CaptureTurn, CaptureEvent]]:
        return ()


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


def consent_given(context: CaptureTurn) -> bool:
    """The guard into drafting: the session already holds messages, and the
    user's latest message was read as consent (FR-01).

    Named rather than inlined because it is the most-read decision in this
    graph. Both halves are required: the messages half is a genuine port of
    `_should_draft` (`reply_generation.py:74`), which returns False with no user
    entry; the consent half replaces that function's phrase list, which is not
    ported — no fixed phrase stands in for the user's word.
    """
    ...


async def _assess_coverage(
    context: CaptureTurn, arguments: ToolArguments
) -> CoverageAssessed: ...


async def _propose_session_topic(
    context: CaptureTurn, arguments: ToolArguments
) -> SessionTopicProposal: ...


async def _propose_note_topic(
    context: CaptureTurn, arguments: ToolArguments
) -> NoteTopicProposal: ...


async def _propose_note_tag(
    context: CaptureTurn, arguments: ToolArguments
) -> NoteTagProposal: ...


async def _propose_note_content(
    context: CaptureTurn, arguments: ToolArguments
) -> NoteContentProposal: ...


async def _assign_session_topic(context: CaptureTurn, event: CaptureEvent) -> None:
    """Put the proposed topic on the session, in memory. `assign_topic` refuses
    a second assignment, which is why `Conversing` withdraws the tool once the
    session has one."""
    ...


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

_CAPTURE_GRAPH = Graph[CaptureTurn, CaptureEvent, CapturePhase](
    states={
        CapturePhase.CONVERSING: Conversing(),
        CapturePhase.DRAFTING: Drafting(),
    },
    transitions={
        CapturePhase.CONVERSING: {
            CapturePhase.DRAFTING: Transition[CaptureTurn, CaptureEvent](
                guard=consent_given
            )
        },
        # Unguarded on purpose. FR-02 requires that note drafting never become
        # terminal, and the cheapest way to guarantee a guard is never
        # permanently unsatisfiable is for there to be no guard at all.
        CapturePhase.DRAFTING: {
            CapturePhase.CONVERSING: Transition[CaptureTurn, CaptureEvent]()
        },
    },
)
