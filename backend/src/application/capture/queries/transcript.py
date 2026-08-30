from typing import Protocol

from application.capture.value_objects import Transcript
from domain.capture.value_objects import SessionId


class TranscriptQueryPort(Protocol):
    async def get_transcript(self, session_id: SessionId) -> Transcript: ...
