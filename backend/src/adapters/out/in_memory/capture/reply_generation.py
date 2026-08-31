import asyncio
from collections.abc import AsyncIterator

from application.capture.value_objects import (
    ConfidenceAssessment,
    ConfidencePointKind,
    DraftContentChunk,
    DraftTagChunk,
    DraftTopicChunk,
    ReplyChunk,
    ReplyTextChunk,
    Transcript,
    TranscriptEntry,
)
from domain.capture.value_objects import Label, MessageRole

_CHUNK_SIZE = 12
_CHUNK_DELAY_SECONDS = 0.01
_DEFAULT_SOLID = "what you've said so far"
_DEFAULT_SHAKY = "the parts you haven't unpacked yet"
_HANDOFF_LINE = "I'll draft a note summarizing our conversation."

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


class DeterministicReplyGenerationAdapter:
    async def generate(
        self,
        transcript: Transcript,
        assessment: ConfidenceAssessment,
    ) -> AsyncIterator[ReplyChunk]:
        if _should_draft(transcript):
            yield ReplyTextChunk(text=_HANDOFF_LINE)

            topic_label = _derive_topic_label(transcript, assessment)
            yield DraftTopicChunk(label=topic_label)

            for tag_label in _derive_tag_labels(assessment):
                yield DraftTagChunk(label=tag_label)

            note_body = _derive_note_body(transcript)
            for start in range(0, len(note_body), _CHUNK_SIZE):
                yield DraftContentChunk(text=note_body[start : start + _CHUNK_SIZE])
                await asyncio.sleep(_CHUNK_DELAY_SECONDS)
            return

        reply = _conversational_reply(assessment)
        async for chunk in _yield_text_chunks(reply):
            yield chunk


def _normalize_phrase(text: str) -> str:
    return text.strip().lower()


def _is_confirmation(content: str) -> bool:
    return _normalize_phrase(content) in _CONFIRMATION_PHRASES


def _last_user_entry(transcript: Transcript) -> TranscriptEntry | None:
    for entry in reversed(transcript):
        if entry.role == MessageRole.USER:
            return entry
    return None


def _should_draft(transcript: Transcript) -> bool:
    last_user = _last_user_entry(transcript)
    if last_user is None:
        return False
    return _is_confirmation(last_user.content.value)


def _user_messages_excluding_confirmation(transcript: Transcript) -> list[str]:
    return [
        entry.content.value.strip()
        for entry in transcript
        if entry.role == MessageRole.USER and not _is_confirmation(entry.content.value)
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
            if point.kind == ConfidencePointKind.SHAKY
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
        if entry.role == MessageRole.USER and _is_confirmation(entry.content.value):
            continue
        speaker = "User" if entry.role == MessageRole.USER else "Agent"
        lines.append(f"{speaker}: {entry.content.value.strip()}")
    return "\n\n".join(lines)


def _conversational_reply(assessment: ConfidenceAssessment) -> str:
    solid = next(
        (
            point.note
            for point in assessment.points
            if point.kind == ConfidencePointKind.SOLID
        ),
        _DEFAULT_SOLID,
    )
    shaky = next(
        (
            point.note
            for point in assessment.points
            if point.kind == ConfidencePointKind.SHAKY
        ),
        _DEFAULT_SHAKY,
    )
    return f"You've got a handle on: {solid}. Let's dig into: {shaky}."


async def _yield_text_chunks(text: str) -> AsyncIterator[ReplyTextChunk]:
    for start in range(0, len(text), _CHUNK_SIZE):
        yield ReplyTextChunk(text=text[start : start + _CHUNK_SIZE])
        await asyncio.sleep(_CHUNK_DELAY_SECONDS)
