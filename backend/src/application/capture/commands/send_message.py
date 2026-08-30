from collections.abc import AsyncIterator

from application.capture.dto import ReplyDeltaEvent, ReplyDoneEvent, ReplyStreamEvent
from application.capture.ports import (
    ConfidenceAssessmentPort,
    ReplyGenerationPort,
    TopicExtractionPort,
    UnitOfWork,
)
from application.capture.queries.transcript import TranscriptQueryPort
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


async def load_open_session_for_turn(
    session_id: SessionId,
    raw_content: str,
    capture_sessions: CaptureSessionRepository,
) -> tuple[CaptureSession, MessageContent]:
    content = MessageContent(value=raw_content)
    session = await capture_sessions.get(session_id)
    if session is None:
        raise CaptureSessionNotFoundError
    if session.status != SessionStatus.OPEN:
        raise CaptureSessionClosedError
    return session, content


class GenerateReplyCommand:
    def __init__(
        self,
        uow: UnitOfWork,
        transcript_query: TranscriptQueryPort,
        topic_extraction: TopicExtractionPort,
        confidence_assessment: ConfidenceAssessmentPort,
        reply_generation: ReplyGenerationPort,
    ) -> None:
        self._uow: UnitOfWork = uow
        self._transcript_query: TranscriptQueryPort = transcript_query
        self._topic_extraction: TopicExtractionPort = topic_extraction
        self._confidence_assessment: ConfidenceAssessmentPort = confidence_assessment
        self._reply_generation: ReplyGenerationPort = reply_generation

    async def handle(
        self,
        session: CaptureSession,
        content: MessageContent,
    ) -> AsyncIterator[ReplyStreamEvent]:
        async with self._uow as uow:
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
                full_text += chunk
                yield ReplyDeltaEvent(text=chunk)

            reply_content = MessageContent(value=full_text)
            agent_message = Message.record(session.id, MessageRole.AGENT, reply_content)
            await uow.messages.add(agent_message)
            await uow.commit()

            yield ReplyDoneEvent(
                message_id=agent_message.id.value,
                content=reply_content.value,
                topic=topic.value,
            )
