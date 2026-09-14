import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from adapters.out.sqlalchemy.capture.capture_session_repository import (
    SqlAlchemyCaptureSessionRepository,
)
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.capture.capture_session import CaptureSession
from domain.capture.ports import CaptureSessionRepository
from domain.capture.value_objects import (
    CapturePhase,
    ConversationRequest,
    Coverage,
    DraftingConsent,
    SessionId,
)
from domain.shared.identity.model import UserId

_OWNER = UserId.new()


class _CommittingCaptureSessionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def get(self, session_id: SessionId) -> CaptureSession | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyCaptureSessionRepository(db_session).get(session_id)

    async def save(self, session: CaptureSession) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyCaptureSessionRepository(db_session).save(session)
            await db_session.commit()


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def repository(request: pytest.FixtureRequest) -> CaptureSessionRepository:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return InMemoryCaptureSessionRepository()
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _CommittingCaptureSessionRepository(session_factory)


async def test_save_then_get_returns_the_saved_session(
    repository: CaptureSessionRepository,
) -> None:
    session = CaptureSession.start(_OWNER)

    await repository.save(session)
    result = await repository.get(session.id)

    assert result == session


async def test_get_returns_none_for_unknown_session_id(
    repository: CaptureSessionRepository,
) -> None:
    result = await repository.get(SessionId.new())

    assert result is None


async def test_save_overwrite_reads_back_assessments_phase_consent_and_request(
    repository: CaptureSessionRepository,
) -> None:
    session = CaptureSession.start(_OWNER)
    session.record_assessment(Coverage(value=0.4))
    session.enter_phase(CapturePhase.DRAFTING)
    session.record_drafting_consent(DraftingConsent())
    session.record_conversation_request(ConversationRequest())

    await repository.save(session)
    session.record_assessment(Coverage(value=0.7))
    await repository.save(session)
    result = await repository.get(session.id)

    assert result is not None
    assert result.assessments == (Coverage(value=0.4), Coverage(value=0.7))
    assert result.phase == CapturePhase.DRAFTING
    assert result.drafting_consent == DraftingConsent()
    assert result.conversation_request == ConversationRequest()
