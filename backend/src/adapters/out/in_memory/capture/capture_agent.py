import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from contextlib import asynccontextmanager

from application.capture.value_objects import (
    ConfidenceAssessment,
    ConfidencePointKind,
    Transcript,
    TranscriptEntry,
)
from domain.capture.instructions import DRAFT_STATE, HANDOFF
from domain.capture.message import Message
from domain.capture.turn import (
    AgentEvent,
    CaptureTurn,
    CoverageAssessed,
    DraftingConsentSignalled,
    NoteContentProduced,
    NoteTagProposed,
    NoteTopicProposed,
    ReplyProduced,
    SessionTopicProposed,
)
from domain.capture.value_objects import (
    Coverage,
    Label,
    MessageRole,
    NoteContent,
    SessionTopic,
)
from domain.shared.graph.model import Tool, ToolResult
from domain.shared.instruction.model import Instruction

_CHUNK_SIZE = 12
_CHUNK_DELAY_SECONDS = 0.01

_MAX_TOPIC_WORDS = 8
_DEFAULT_TOPIC = "Untitled capture session"

_CONFIRMATION_PHRASES = frozenset(
    {
        "that's all",
        "that's everything",
        "we're done",
        "i'm done",
        "nothing more",
        "that covers it",
    }
)


class DeterministicCaptureAgentAdapter:
    @asynccontextmanager
    async def converse(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
        instruction: Instruction,
    ) -> AsyncGenerator[AsyncIterator[AgentEvent], None]:
        events = self._events(turn, tools, instruction)
        try:
            yield events
        finally:
            await events.aclose()

    async def _events(
        self,
        turn: CaptureTurn,
        tools: Sequence[Tool[CaptureTurn, ToolResult]],
        instruction: Instruction,
    ) -> AsyncGenerator[AgentEvent, None]:
        tools_by_name = {tool.name: tool for tool in tools}
        last_user = _last_user_message(turn)

        if (
            last_user is not None
            and _is_confirmation(last_user.content.value)
            and "signal_drafting_consent" in tools_by_name
        ):
            yield DraftingConsentSignalled()
            return

        if _has_block(instruction, DRAFT_STATE):
            if _has_block(instruction, HANDOFF):
                async for chunk in _yield_reply(_block_text(instruction, HANDOFF)):
                    yield chunk
            transcript = _transcript(turn)
            assessment = _assess(transcript)
            topic_label = _derive_topic_label(transcript, assessment)
            yield NoteTopicProposed(label=topic_label)
            for tag_label in _derive_tag_labels(assessment):
                yield NoteTagProposed(label=tag_label)
            note_body = _derive_note_body(transcript)
            async for chunk in _yield_note_content(note_body):
                yield chunk
            return

        if turn.session.topic is None and last_user is not None:
            yield SessionTopicProposed(topic=_session_topic_from_message(last_user))

        transcript = _transcript(turn)
        assessment = _assess(transcript)
        if "assess_coverage" in tools_by_name:
            yield CoverageAssessed(
                coverage=Coverage(value=assessment.coverage_confidence)
            )
        reply = _conversational_reply(instruction)
        async for chunk in _yield_reply(reply):
            yield chunk


def _has_block(instruction: Instruction, name: str) -> bool:
    return any(block.name == name for block in instruction.blocks)


def _block_text(instruction: Instruction, name: str) -> str:
    for block in instruction.blocks:
        if block.name == name:
            return block.text
    raise KeyError(name)


def _conversational_reply(instruction: Instruction) -> str:
    return " ".join(block.text for block in instruction.blocks)


def _transcript(turn: CaptureTurn) -> Transcript:
    return [
        TranscriptEntry(role=message.role, content=message.content)
        for message in turn.messages
    ]


def _session_topic_from_message(message: Message) -> SessionTopic:
    words = message.content.value.strip().split()
    value = " ".join(words[:_MAX_TOPIC_WORDS]) or _DEFAULT_TOPIC
    return SessionTopic(value=value)


def _normalize_phrase(text: str) -> str:
    return text.strip().lower()


def _is_confirmation(content: str) -> bool:
    return _normalize_phrase(content) in _CONFIRMATION_PHRASES


def _last_user_message(turn: CaptureTurn):
    for message in reversed(turn.messages):
        if message.role is MessageRole.USER:
            return message
    return None


def _assess(transcript: Transcript) -> ConfidenceAssessment:
    from application.capture.value_objects import ConfidencePoint

    user_entries = [entry for entry in transcript if entry.role is MessageRole.USER]
    if not user_entries:
        return ConfidenceAssessment(points=[], coverage_confidence=0.0)

    latest = user_entries[-1]
    return ConfidenceAssessment(
        points=[
            ConfidencePoint(
                kind=ConfidencePointKind.SOLID,
                note=f"You've articulated: {latest.content.value.strip()}",
            ),
            ConfidencePoint(
                kind=ConfidencePointKind.SHAKY,
                note=f"The details behind: {latest.content.value.strip()}",
            ),
        ],
        coverage_confidence=0.0,
    )


def _user_messages_excluding_confirmation(transcript: Transcript) -> list[str]:
    return [
        entry.content.value.strip()
        for entry in transcript
        if entry.role is MessageRole.USER and not _is_confirmation(entry.content.value)
    ]


def _derive_topic_label(
    transcript: Transcript, assessment: ConfidenceAssessment
) -> Label:
    user_messages = _user_messages_excluding_confirmation(transcript)
    base = user_messages[0] if user_messages else "Untitled capture session"

    shaky = next(
        (
            point.note
            for point in assessment.points
            if point.kind is ConfidencePointKind.SHAKY
        ),
        None,
    )
    if shaky:
        return Label(value=f"{shaky} in {base}")
    return Label(value=base)


def _derive_tag_labels(assessment: ConfidenceAssessment) -> list[Label]:
    return [Label(value=point.note) for point in assessment.points]


def _derive_note_body(transcript: Transcript) -> str:
    lines: list[str] = []
    for entry in transcript:
        if entry.role is MessageRole.USER and _is_confirmation(entry.content.value):
            continue
        speaker = "User" if entry.role is MessageRole.USER else "Agent"
        lines.append(f"{speaker}: {entry.content.value.strip()}")
    return "\n\n".join(lines)


async def _yield_reply(text: str) -> AsyncIterator[ReplyProduced]:
    for start in range(0, len(text), _CHUNK_SIZE):
        yield ReplyProduced(text=text[start : start + _CHUNK_SIZE])
        await asyncio.sleep(_CHUNK_DELAY_SECONDS)


async def _yield_note_content(text: str) -> AsyncIterator[NoteContentProduced]:
    for start in range(0, len(text), _CHUNK_SIZE):
        yield NoteContentProduced(
            content=NoteContent(value=text[start : start + _CHUNK_SIZE])
        )
        await asyncio.sleep(_CHUNK_DELAY_SECONDS)
