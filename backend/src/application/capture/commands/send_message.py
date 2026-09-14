from collections.abc import AsyncIterator
from dataclasses import dataclass

from application.capture.dto import (
    DraftDeltaEvent,
    DraftDoneEvent,
    DraftTagEvent,
    DraftTopicEvent,
    ReplyDeltaEvent,
    ReplyDoneEvent,
    ReplyStreamEvent,
)
from application.capture.ports import UnitOfWork
from domain.capture.capture_session import CaptureSession
from domain.capture.deps import RepositoryCaptureDeps
from domain.capture.exceptions import (
    CaptureSessionClosedError,
    CaptureSessionNotFoundError,
    DraftTopicMissingError,
    NoteNotFoundError,
)
from domain.capture.graph import CaptureMachine
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.ports import CaptureAgentPort, CaptureSessionRepository
from domain.capture.turn import (
    AgentEvent,
    AssistantMessageRecorded,
    CaptureTurn,
    DraftCompleted,
    NoteContentProduced,
    NoteTagProposed,
    NoteTopicProposed,
    ReplyProduced,
    UserMessageRecorded,
)
from domain.capture.value_objects import (
    CapturePhase,
    MessageContent,
    MessageRole,
    SessionId,
    SessionStatus,
)
from domain.capture.vocabulary import VocabularyResolver
from domain.shared.identity.model import UserId


@dataclass
class _TurnBuffers:
    full_text: str = ""
    agent_message: Message | None = None


class GenerateReplyCommand:
    def __init__(
        self,
        uow: UnitOfWork,
        capture_agent: CaptureAgentPort,
        vocabulary: VocabularyResolver,
    ) -> None:
        self._uow: UnitOfWork = uow
        self._capture_agent: CaptureAgentPort = capture_agent
        self._vocabulary: VocabularyResolver = vocabulary

    async def guard_session(
        self, owner: UserId, session_id: SessionId, raw_content: str
    ) -> MessageContent:
        content = MessageContent(value=raw_content)
        async with self._uow as uow:
            _ = await self._get_open_session(uow.capture_sessions, owner, session_id)
        return content

    async def handle(
        self,
        owner: UserId,
        session_id: SessionId,
        content: MessageContent,
    ) -> AsyncIterator[ReplyStreamEvent]:
        async with self._uow as uow:
            session = await self._get_open_session(
                uow.capture_sessions, owner, session_id
            )
            prior = await uow.messages.history(session.id)
            user_message = Message.record(session.id, MessageRole.USER, content)

            note: Note | None = None
            if session.note_id is not None:
                note = await uow.notes.get(session.note_id)
                if note is None:
                    raise NoteNotFoundError

            turn = CaptureTurn(session=session, messages=prior, note=note)
            deps = RepositoryCaptureDeps(
                messages=uow.messages,
                notes=uow.notes,
                topics=uow.topics,
                tags=uow.tags,
                note_vocabulary=uow.note_vocabulary,
                vocabulary=self._vocabulary,
            )
            machine = CaptureMachine(turn, deps)
            await machine.apply(UserMessageRecorded(message=user_message))

            buffers = _TurnBuffers()
            async for event in self._dispatch(machine, turn, buffers):
                yield event

            context = machine.context
            session = context.session
            draft_done_event: DraftDoneEvent | None = None
            persisted_note = context.note
            draft = context.draft
            if (
                persisted_note is not None
                and draft is not None
                and draft.topic is not None
            ):
                draft_done_event = DraftDoneEvent(
                    note_id=persisted_note.id.value,
                    topic=draft.topic.label.value,
                    content=persisted_note.content.value,
                    tags=[tag.label.value for tag in draft.tags],
                )

            if buffers.agent_message is None:
                done_message_id = user_message.id.value
                done_content = buffers.full_text
            else:
                done_message_id = buffers.agent_message.id.value
                done_content = buffers.agent_message.content.value
            topic_value = session.topic.value if session.topic is not None else ""
            assessments = session.assessments
            coverage_confidence = assessments[-1].value if assessments else 0.0
            done_event = ReplyDoneEvent(
                message_id=done_message_id,
                content=done_content,
                topic=topic_value,
                coverage_confidence=coverage_confidence,
            )

            await uow.capture_sessions.save(session)
            await uow.commit()

        if draft_done_event is not None:
            yield draft_done_event
        yield done_event

    async def _dispatch(
        self,
        machine: CaptureMachine,
        turn: CaptureTurn,
        buffers: _TurnBuffers,
    ) -> AsyncIterator[ReplyStreamEvent]:
        if CapturePhase.DRAFTING in machine.available_transitions():
            _ = await machine.transition(CapturePhase.DRAFTING)

        if machine.current_state_name is CapturePhase.CONVERSING:
            async for event in self._conversing_stream(machine, turn, buffers):
                yield event
            if CapturePhase.DRAFTING in machine.available_transitions():
                _ = await machine.transition(CapturePhase.DRAFTING)

        if machine.current_state_name is CapturePhase.DRAFTING:
            async for event in self._drafting_stream(machine, turn, buffers):
                yield event

    async def _conversing_stream(
        self,
        machine: CaptureMachine,
        turn: CaptureTurn,
        buffers: _TurnBuffers,
    ) -> AsyncIterator[ReplyStreamEvent]:
        async for event in self._open_stream(machine, turn, buffers):
            yield event

    async def _drafting_stream(
        self,
        machine: CaptureMachine,
        turn: CaptureTurn,
        buffers: _TurnBuffers,
    ) -> AsyncIterator[ReplyStreamEvent]:
        async for event in self._open_stream(machine, turn, buffers):
            yield event

    async def _open_stream(
        self,
        machine: CaptureMachine,
        turn: CaptureTurn,
        buffers: _TurnBuffers,
    ) -> AsyncIterator[ReplyStreamEvent]:
        reply_buffer = ""
        drafting = machine.current_state_name is CapturePhase.DRAFTING
        instruction = machine.build_instruction()
        async with self._capture_agent.converse(
            turn, machine.get_tools(), instruction
        ) as events:
            async for event in events:
                await machine.apply(event)
                mapped = self._to_reply_stream_event(machine, event)
                if mapped is None:
                    continue
                stream_event, extra_text = mapped
                if extra_text is not None:
                    reply_buffer += extra_text
                    buffers.full_text += extra_text
                yield stream_event
        if drafting:
            await machine.apply(DraftCompleted())
        if reply_buffer:
            assistant = Message.record(
                turn.session.id,
                MessageRole.AGENT,
                MessageContent(value=reply_buffer),
            )
            await machine.apply(AssistantMessageRecorded(message=assistant))
            buffers.agent_message = assistant

    def _to_reply_stream_event(
        self,
        machine: CaptureMachine,
        event: AgentEvent,
    ) -> tuple[ReplyStreamEvent, str | None] | None:
        if isinstance(event, ReplyProduced):
            return ReplyDeltaEvent(text=event.text), event.text
        draft = machine.context.draft
        if isinstance(event, NoteTopicProposed):
            if draft is None or draft.topic is None:
                raise DraftTopicMissingError
            return (
                DraftTopicEvent(
                    label=draft.topic.label.value,
                    reused=draft.topic_reused,
                ),
                None,
            )
        if isinstance(event, NoteTagProposed):
            if draft is None or draft.topic is None or not draft.tags:
                raise DraftTopicMissingError
            tag = draft.tags[-1]
            return (
                DraftTagEvent(
                    label=tag.label.value,
                    reused=draft.tag_reused[-1],
                ),
                None,
            )
        if isinstance(event, NoteContentProduced):
            if draft is None or draft.topic is None:
                raise DraftTopicMissingError
            return DraftDeltaEvent(text=event.content.value), None
        return None

    async def _get_open_session(
        self,
        capture_sessions: CaptureSessionRepository,
        owner: UserId,
        session_id: SessionId,
    ) -> CaptureSession:
        _ = owner
        session = await capture_sessions.get(session_id)
        if session is None:
            raise CaptureSessionNotFoundError
        if session.status != SessionStatus.OPEN:
            raise CaptureSessionClosedError
        return session
