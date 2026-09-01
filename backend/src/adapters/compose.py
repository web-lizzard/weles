from typing import cast

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.in_memory.capture.confidence_assessment import (
    DeterministicConfidenceAssessmentAdapter,
)
from adapters.out.in_memory.capture.embedding import DeterministicEmbeddingAdapter
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.capture.reply_generation import (
    DeterministicReplyGenerationAdapter,
)
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_extraction import (
    DeterministicTopicExtractionAdapter,
)
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from adapters.out.in_memory.capture.transcript_query import (
    InMemoryTranscriptQueryAdapter,
)
from adapters.out.in_memory.capture.unit_of_work import InMemoryUnitOfWork
from application.capture.commands.send_message import GenerateReplyCommand
from application.capture.commands.start_capture_session import (
    StartCaptureSessionCommand,
)
from application.capture.ports import UnitOfWork
from application.capture.services.vocabulary import VocabularyResolver
from domain.capture.ports import CaptureSessionRepository

_store = InMemoryMessageStore()
_capture_session_repository = InMemoryCaptureSessionRepository()
_message_repository = InMemoryMessageRepository(_store)
_note_repository = InMemoryNoteRepository()
_topic_repository = InMemoryTopicRepository()
_tag_repository = InMemoryTagRepository()
_transcript_query = InMemoryTranscriptQueryAdapter(_store)
_topic_extraction = DeterministicTopicExtractionAdapter()
_confidence_assessment = DeterministicConfidenceAssessmentAdapter()
_reply_generation = DeterministicReplyGenerationAdapter()
_embedding = DeterministicEmbeddingAdapter()
_vocabulary = VocabularyResolver(_embedding)


def _unit_of_work() -> UnitOfWork:
    return cast(
        UnitOfWork,
        cast(
            object,
            InMemoryUnitOfWork(
                _capture_session_repository,
                _message_repository,
                _store,
                _note_repository,
                _topic_repository,
                _tag_repository,
            ),
        ),
    )


def get_capture_session_repository() -> CaptureSessionRepository:
    return _capture_session_repository


def get_start_capture_session_command() -> StartCaptureSessionCommand:
    return StartCaptureSessionCommand(uow=_unit_of_work())


def get_generate_reply_command() -> GenerateReplyCommand:
    return GenerateReplyCommand(
        capture_sessions=_capture_session_repository,
        uow=_unit_of_work(),
        transcript_query=_transcript_query,
        topic_extraction=_topic_extraction,
        confidence_assessment=_confidence_assessment,
        reply_generation=_reply_generation,
        vocabulary=_vocabulary,
    )
