from collections.abc import AsyncIterator

from application.capture.dto import (
    DraftDeltaEvent,
    DraftDoneEvent,
    DraftTagEvent,
    DraftTopicEvent,
    ReplyDeltaEvent,
    ReplyDoneEvent,
    ReplyStreamEvent,
)
from application.capture.exceptions import DraftTopicMissingError
from application.capture.ports import (
    ConfidenceAssessmentPort,
    ReplyGenerationPort,
    TopicExtractionPort,
    UnitOfWork,
)
from application.capture.queries.transcript import TranscriptQueryPort
from application.capture.services.vocabulary import VocabularyResolver
from application.capture.value_objects import (
    DraftTagChunk,
    DraftTopicChunk,
    ReplyTextChunk,
)
from domain.capture.capture_session import CaptureSession
from domain.capture.exceptions import (
    CaptureSessionClosedError,
    CaptureSessionNotFoundError,
    NoteNotFoundError,
)
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.ports import CaptureSessionRepository
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.value_objects import (
    MessageContent,
    MessageRole,
    NoteContent,
    SessionId,
    SessionStatus,
)


class GenerateReplyCommand:
    def __init__(
        self,
        capture_sessions: CaptureSessionRepository,
        uow: UnitOfWork,
        transcript_query: TranscriptQueryPort,
        topic_extraction: TopicExtractionPort,
        confidence_assessment: ConfidenceAssessmentPort,
        reply_generation: ReplyGenerationPort,
        vocabulary: VocabularyResolver,
    ) -> None:
        self._capture_sessions: CaptureSessionRepository = capture_sessions
        self._uow: UnitOfWork = uow
        self._transcript_query: TranscriptQueryPort = transcript_query
        self._topic_extraction: TopicExtractionPort = topic_extraction
        self._confidence_assessment: ConfidenceAssessmentPort = confidence_assessment
        self._reply_generation: ReplyGenerationPort = reply_generation
        self._vocabulary: VocabularyResolver = vocabulary

    async def guard_session(
        self, session_id: SessionId, raw_content: str
    ) -> MessageContent:
        content = MessageContent(value=raw_content)
        _ = await self._get_open_session(self._capture_sessions, session_id)
        return content

    async def handle(
        self,
        session_id: SessionId,
        content: MessageContent,
    ) -> AsyncIterator[ReplyStreamEvent]:
        async with self._uow as uow:
            session = await self._get_open_session(uow.capture_sessions, session_id)

            user_message = Message.record(session.id, MessageRole.USER, content)
            await uow.messages.add(user_message)

            if session.topic is None:
                topic = await self._topic_extraction.extract(content)
                session.assign_topic(topic)
                await uow.capture_sessions.save(session)
            else:
                topic = session.topic

            transcript = await self._transcript_query.get_transcript(session.id)
            assessment = await self._confidence_assessment.assess(transcript)

            full_text = ""
            draft_text = ""
            saw_draft = False
            resolved_topic: Topic | None = None
            resolved_tags: list[Tag] = []
            draft_done_event: DraftDoneEvent | None = None

            async for chunk in self._reply_generation.generate(transcript, assessment):
                if isinstance(chunk, ReplyTextChunk):
                    full_text += chunk.text
                    yield ReplyDeltaEvent(text=chunk.text)
                elif isinstance(chunk, DraftTopicChunk):
                    saw_draft = True
                    resolution = await self._vocabulary.resolve_topic(
                        chunk.label,
                        uow.topics,
                    )
                    resolved_topic = resolution.topic
                    yield DraftTopicEvent(
                        label=resolved_topic.label.value, reused=resolution.reused
                    )
                elif isinstance(chunk, DraftTagChunk):
                    saw_draft = True
                    if resolved_topic is None:
                        raise DraftTopicMissingError
                    tag_resolution = await self._vocabulary.resolve_tag(
                        chunk.label, uow.tags
                    )
                    tag = tag_resolution.tag
                    resolved_tags.append(tag)
                    yield DraftTagEvent(
                        label=tag.label.value, reused=tag_resolution.reused
                    )
                else:
                    saw_draft = True
                    if resolved_topic is None:
                        raise DraftTopicMissingError
                    draft_text += chunk.text
                    yield DraftDeltaEvent(text=chunk.text)

            reply_content = MessageContent(value=full_text)
            agent_message = Message.record(session.id, MessageRole.AGENT, reply_content)
            await uow.messages.add(agent_message)

            if saw_draft:
                if resolved_topic is None:
                    raise DraftTopicMissingError
                note_content = NoteContent(value=draft_text)
                if session.note_id is not None:
                    note = await uow.notes.get(session.note_id)
                    if note is None:
                        raise NoteNotFoundError
                    await self._apply_redraft(
                        uow, note, resolved_topic, resolved_tags, note_content
                    )
                else:
                    note = session.draft_note(
                        resolved_topic,
                        note_content,
                        resolved_tags,
                    )
                    await uow.notes.add(note)
                    await uow.capture_sessions.save(session)
                draft_done_event = DraftDoneEvent(
                    note_id=note.id.value,
                    topic=resolved_topic.label.value,
                    content=note.content.value,
                    tags=[tag.label.value for tag in resolved_tags],
                )

            done_event = ReplyDoneEvent(
                message_id=agent_message.id.value,
                content=reply_content.value,
                topic=topic.value,
                coverage_confidence=assessment.coverage_confidence,
            )
            await uow.commit()

        if draft_done_event is not None:
            yield draft_done_event
        yield done_event

    async def _apply_redraft(
        self,
        _uow: UnitOfWork,
        _note: Note,
        _topic: Topic,
        _tags: list[Tag],
        _content: NoteContent,
    ) -> None:
        raise NotImplementedError

    async def _get_open_session(
        self,
        capture_sessions: CaptureSessionRepository,
        session_id: SessionId,
    ) -> CaptureSession:
        session = await capture_sessions.get(session_id)
        if session is None:
            raise CaptureSessionNotFoundError
        if session.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError
        return session
