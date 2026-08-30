from collections.abc import Callable

import pytest

from adapters.out.in_memory.capture.capture_session_repository import (
    InMemoryCaptureSessionRepository,
)
from domain.capture.capture_session import CaptureSession
from domain.capture.ports import CaptureSessionRepository
from domain.capture.value_objects import SessionId

_IMPLEMENTATIONS: list[Callable[[], CaptureSessionRepository]] = [
    InMemoryCaptureSessionRepository,
]


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_save_then_get_returns_the_saved_session(
    make_repository: Callable[[], CaptureSessionRepository],
) -> None:
    repository = make_repository()
    session = CaptureSession.start()

    await repository.save(session)
    result = await repository.get(session.id)

    assert result == session


@pytest.mark.parametrize("make_repository", _IMPLEMENTATIONS, ids=["in_memory"])
async def test_get_returns_none_for_unknown_session_id(
    make_repository: Callable[[], CaptureSessionRepository],
) -> None:
    repository = make_repository()

    result = await repository.get(SessionId.new())

    assert result is None
