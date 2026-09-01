from collections.abc import AsyncIterator

from application.capture.dto import ReplyDeltaEvent, ReplyDoneEvent, ReplyStreamEvent
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
)
from domain.capture.message import Message
from domain.capture.ports import CaptureSessionRepository
from domain.capture.value_objects import (
    MessageContent,
    MessageRole,
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
            async for chunk in self._reply_generation.generate(transcript, assessment):
                if isinstance(chunk, ReplyTextChunk):
                    full_text += chunk.text
                    yield ReplyDeltaEvent(text=chunk.text)
                elif isinstance(chunk, DraftTopicChunk):
                    raise NotImplementedError
                elif isinstance(chunk, DraftTagChunk):
                    raise NotImplementedError
                else:
                    raise NotImplementedError

            reply_content = MessageContent(value=full_text)
            agent_message = Message.record(session.id, MessageRole.AGENT, reply_content)
            await uow.messages.add(agent_message)

            done_event = ReplyDoneEvent(
                message_id=agent_message.id.value,
                content=reply_content.value,
                topic=topic.value,
                coverage_confidence=assessment.coverage_confidence,
            )
            await uow.commit()

        yield done_event

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
