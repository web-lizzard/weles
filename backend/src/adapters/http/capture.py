from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse

from adapters.compose import (
    get_generate_reply_command,
    get_start_capture_session_command,
)
from application.capture.commands.send_message import GenerateReplyCommand
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from application.capture.dto import (
    ReplyStreamEvent,
    SendMessageRequestDTO,
    StartCaptureSessionResponseDTO,
)
from domain.capture.value_objects import MessageContent, SessionId

router = APIRouter()


async def get_turn_context(
    session_id: UUID,
    body: SendMessageRequestDTO,
    command: Annotated[GenerateReplyCommand, Depends(get_generate_reply_command)],
) -> MessageContent:
    return await command.guard_session(SessionId(value=session_id), body.content)


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
    session_id: UUID,
    content: Annotated[MessageContent, Depends(get_turn_context)],
    command: Annotated[GenerateReplyCommand, Depends(get_generate_reply_command)],
) -> AsyncIterator[ReplyStreamEvent]:
    async for event in command.handle(SessionId(value=session_id), content):
        yield event
