from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse

from application.capture.commands.send_message import (
    GenerateReplyCommand,
    load_open_session_for_turn,
)
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from application.capture.dto import (
    ReplyStreamEvent,
    SendMessageRequestDTO,
    StartCaptureSessionResponseDTO,
)
from domain.capture.capture_session import CaptureSession
from domain.capture.ports import CaptureSessionRepository
from domain.capture.value_objects import MessageContent, SessionId

router = APIRouter()


def get_capture_session_repository() -> CaptureSessionRepository:
    raise NotImplementedError


def get_start_capture_session_command() -> StartCaptureSessionCommand:
    raise NotImplementedError


def get_generate_reply_command() -> GenerateReplyCommand:
    raise NotImplementedError


async def get_turn_context(
    session_id: UUID,
    body: SendMessageRequestDTO,
    capture_sessions: Annotated[
        CaptureSessionRepository, Depends(get_capture_session_repository)
    ],
) -> tuple[CaptureSession, MessageContent]:
    return await load_open_session_for_turn(
        SessionId(value=session_id),
        body.content,
        capture_sessions,
    )


@router.post("/capture-sessions")
async def start_capture_session(
    command: Annotated[
        StartCaptureSessionCommand, Depends(get_start_capture_session_command)
    ],
) -> StartCaptureSessionResponseDTO:
    return await command.handle()


@router.post(
    "/capture-sessions/{session_id}/messages",
    response_class=EventSourceResponse,
)
async def send_message(
    turn: Annotated[tuple[CaptureSession, MessageContent], Depends(get_turn_context)],
    command: Annotated[GenerateReplyCommand, Depends(get_generate_reply_command)],
) -> AsyncIterator[ReplyStreamEvent]:
    session, content = turn
    async for event in command.handle(session, content):
        yield event
