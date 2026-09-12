from collections.abc import AsyncIterator
from dataclasses import dataclass, field

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
from domain.capture.deps import NULL_CAPTURE_DEPS
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
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.turn import (
    AgentEvent,
    AssistantMessageRecorded,
    CaptureTurn,
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
    NoteContent,
    SessionId,
    SessionStatus,
)
from domain.capture.vocabulary import VocabularyResolver


@dataclass
class _TurnBuffers:
    full_text: str = ""
    draft_text: str = ""
    agent_message: Message | None = None
    resolved_topic: Topic | None = None
    resolved_tags: list[Tag] = field(default_factory=list)


class GenerateReplyCommand:
    def __init__(
        self,
        capture_sessions: CaptureSessionRepository,
        uow: UnitOfWork,
        capture_agent: CaptureAgentPort,
        vocabulary: VocabularyResolver,
    ) -> None:
        self._capture_sessions: CaptureSessionRepository = capture_sessions
        self._uow: UnitOfWork = uow
        self._capture_agent: CaptureAgentPort = capture_agent
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
            prior = await uow.messages.history(session.id)
            user_message = Message.record(session.id, MessageRole.USER, content)

            note: Note | None = None
            if session.note_id is not None:
                note = await uow.notes.get(session.note_id)
                if note is None:
                    raise NoteNotFoundError

            turn = CaptureTurn(session=session, messages=prior, note=note)
            machine = CaptureMachine(turn, NULL_CAPTURE_DEPS)
            await machine.apply(UserMessageRecorded(message=user_message))

            buffers = _TurnBuffers()
            async for event in self._dispatch(uow, machine, turn, buffers):
                yield event

            context = machine.context
            session = context.session
            note_to_save: Note | None = None
            if buffers.resolved_topic is not None:
                note_content = NoteContent(value=buffers.draft_text)
                if session.note_id is not None:
                    persisted_note = await uow.notes.get(session.note_id)
                    if persisted_note is None:
                        raise NoteNotFoundError
                    await self._apply_redraft(
                        uow,
                        persisted_note,
                        buffers.resolved_topic,
                        buffers.resolved_tags,
                        note_content,
                    )
                    note_to_save = persisted_note
                else:
                    note_to_save = session.draft_note(
                        buffers.resolved_topic,
                        note_content,
                        buffers.resolved_tags,
                    )
                draft_done_event = DraftDoneEvent(
                    note_id=note_to_save.id.value,
                    topic=buffers.resolved_topic.label.value,
                    content=note_to_save.content.value,
                    tags=[tag.label.value for tag in buffers.resolved_tags],
                )
            elif buffers.draft_text or buffers.resolved_tags:
                raise DraftTopicMissingError
            else:
                draft_done_event = None

            if buffers.agent_message is None:
                done_message_id = user_message.id.value
                done_content = buffers.full_text
            else:
                done_message_id = buffers.agent_message.id.value
                done_content = buffers.agent_message.content.value
            topic_value = session.topic.value if session.topic is not None else ""
            done_event = ReplyDoneEvent(
                message_id=done_message_id,
                content=done_content,
                topic=topic_value,
                coverage_confidence=context.coverage_confidence,
            )

            prior_ids = {message.id.value for message in prior}
            for message in context.messages:
                if message.id.value not in prior_ids:
                    await uow.messages.add(message)
            if note_to_save is not None:
                await uow.notes.add(note_to_save)
            await uow.capture_sessions.save(session)
            await uow.commit()

        if draft_done_event is not None:
            yield draft_done_event
        yield done_event

    async def _dispatch(
        self,
        uow: UnitOfWork,
        machine: CaptureMachine,
        turn: CaptureTurn,
        buffers: _TurnBuffers,
    ) -> AsyncIterator[ReplyStreamEvent]:
        if CapturePhase.DRAFTING in machine.available_transitions():
            _ = await machine.transition(CapturePhase.DRAFTING)

        if machine.current_state_name is CapturePhase.CONVERSING:
            async for event in self._conversing_stream(uow, machine, turn, buffers):
                yield event
            if CapturePhase.DRAFTING in machine.available_transitions():
                _ = await machine.transition(CapturePhase.DRAFTING)

        if machine.current_state_name is CapturePhase.DRAFTING:
            async for event in self._drafting_stream(uow, machine, turn, buffers):
                yield event

    async def _conversing_stream(
        self,
        uow: UnitOfWork,
        machine: CaptureMachine,
        turn: CaptureTurn,
        buffers: _TurnBuffers,
    ) -> AsyncIterator[ReplyStreamEvent]:
        async for event in self._open_stream(uow, machine, turn, buffers):
            yield event

    async def _drafting_stream(
        self,
        uow: UnitOfWork,
        machine: CaptureMachine,
        turn: CaptureTurn,
        buffers: _TurnBuffers,
    ) -> AsyncIterator[ReplyStreamEvent]:
        async for event in self._open_stream(uow, machine, turn, buffers):
            yield event

    async def _open_stream(
        self,
        uow: UnitOfWork,
        machine: CaptureMachine,
        turn: CaptureTurn,
        buffers: _TurnBuffers,
    ) -> AsyncIterator[ReplyStreamEvent]:
        reply_buffer = ""
        async with self._capture_agent.converse(turn, machine.get_tools()) as events:
            async for event in events:
                await machine.apply(event)
                mapped = await self._map_agent_event(
                    uow, event, buffers.resolved_topic, buffers.resolved_tags
                )
                if mapped is None:
                    continue
                stream_event, buffers.resolved_topic, extra_text = mapped
                if extra_text is not None:
                    if isinstance(stream_event, ReplyDeltaEvent):
                        reply_buffer += extra_text
                        buffers.full_text += extra_text
                    else:
                        buffers.draft_text += extra_text
                yield stream_event
        if reply_buffer:
            assistant = Message.record(
                turn.session.id,
                MessageRole.AGENT,
                MessageContent(value=reply_buffer),
            )
            await machine.apply(AssistantMessageRecorded(message=assistant))
            buffers.agent_message = assistant

    async def _map_agent_event(
        self,
        uow: UnitOfWork,
        event: AgentEvent,
        resolved_topic: Topic | None,
        resolved_tags: list[Tag],
    ) -> tuple[ReplyStreamEvent, Topic | None, str | None] | None:
        if isinstance(event, ReplyProduced):
            return ReplyDeltaEvent(text=event.text), resolved_topic, event.text
        if isinstance(event, NoteTopicProposed):
            resolution = await self._vocabulary.resolve_topic(event.label, uow.topics)
            return (
                DraftTopicEvent(
                    label=resolution.topic.label.value, reused=resolution.reused
                ),
                resolution.topic,
                None,
            )
        if isinstance(event, NoteTagProposed):
            if resolved_topic is None:
                raise DraftTopicMissingError
            tag_resolution = await self._vocabulary.resolve_tag(event.label, uow.tags)
            resolved_tags.append(tag_resolution.tag)
            return (
                DraftTagEvent(
                    label=tag_resolution.tag.label.value,
                    reused=tag_resolution.reused,
                ),
                resolved_topic,
                None,
            )
        if isinstance(event, NoteContentProduced):
            if resolved_topic is None:
                raise DraftTopicMissingError
            return (
                DraftDeltaEvent(text=event.content.value),
                resolved_topic,
                event.content.value,
            )
        return None

    async def _apply_redraft(
        self,
        uow: UnitOfWork,
        note: Note,
        topic: Topic,
        tags: list[Tag],
        content: NoteContent,
    ) -> None:
        current = await uow.note_vocabulary.resolve(note)

        note.change_topic(topic)

        resolved_ids = {tag.id for tag in tags}
        current_ids = {tag.id for tag in current.tags}
        for tag in current.tags:
            if tag.id not in resolved_ids:
                note.remove_tag(tag)

        for tag in tags:
            if tag.id not in current_ids:
                note.add_tag(tag)

        note.update_content(content)

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
