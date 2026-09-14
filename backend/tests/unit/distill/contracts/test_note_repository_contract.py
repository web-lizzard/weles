from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from domain.distill.note import Note
from domain.distill.ports import NoteRepository
from domain.distill.value_objects import (
    DistillationStatus,
    NoteContent,
    NoteId,
    SessionId,
    TagSnapshot,
    TopicSnapshot,
)
from domain.shared.identity.model import UserId


class _CommittingNoteRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = session_factory

    async def save(self, note: Note) -> None:
        async with self._session_factory() as db_session:
            await SqlAlchemyNoteRepository(db_session).save(note)
            await db_session.commit()

    async def get(self, note_id: NoteId) -> Note | None:
        async with self._session_factory() as db_session:
            return await SqlAlchemyNoteRepository(db_session).get(note_id)

    async def list_all(self) -> list[Note]:
        async with self._session_factory() as db_session:
            return await SqlAlchemyNoteRepository(db_session).list_all()


def _sample_note(owner_id: UserId | None = None) -> Note:
    stamped_at = datetime.now(UTC)
    return Note(
        id=NoteId(value=uuid4()),
        owner_id=owner_id if owner_id is not None else UserId.new(),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value="We discussed how connections are established."),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=DistillationStatus.GENERATING,
        approved_at=stamped_at,
        created_at=stamped_at,
        updated_at=stamped_at,
    )


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def note_repository(request: pytest.FixtureRequest) -> NoteRepository:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        return InMemoryNoteRepository()
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    return _CommittingNoteRepository(session_factory)


async def test_save_then_get_returns_the_saved_note(
    note_repository: NoteRepository,
) -> None:
    note = _sample_note()

    await note_repository.save(note)
    result = await note_repository.get(note.id)

    assert result == note


async def test_get_returns_none_for_unknown_note_id(
    note_repository: NoteRepository,
) -> None:
    result = await note_repository.get(NoteId(value=uuid4()))

    assert result is None


async def test_second_save_with_same_id_overwrites(
    note_repository: NoteRepository,
) -> None:
    original = _sample_note()
    updated = original.model_copy(
        update={"content": NoteContent(value="Updated body text.")}
    )

    await note_repository.save(original)
    await note_repository.save(updated)
    result = await note_repository.get(original.id)

    assert result == updated


async def test_list_all_returns_every_saved_note(
    note_repository: NoteRepository,
) -> None:
    first = _sample_note()
    second = _sample_note()

    await note_repository.save(first)
    await note_repository.save(second)
    result = await note_repository.list_all()

    assert result == [first, second] or result == [second, first]


async def test_second_save_reorders_tags_and_drops_removed_ones(
    note_repository: NoteRepository,
) -> None:
    stamped_at = datetime.now(UTC)
    alpha = TagSnapshot(id=uuid4(), label="alpha")
    beta = TagSnapshot(id=uuid4(), label="beta")
    gamma = TagSnapshot(id=uuid4(), label="gamma")
    note = Note(
        id=NoteId(value=uuid4()),
        owner_id=UserId.new(),
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="Topics"),
        content=NoteContent(value="Tagged note."),
        tags=[alpha, beta, gamma],
        distillation_status=DistillationStatus.GENERATING,
        approved_at=stamped_at,
        created_at=stamped_at,
        updated_at=stamped_at,
    )

    await note_repository.save(note)
    reordered = note.model_copy(update={"tags": [beta, alpha]})
    await note_repository.save(reordered)
    result = await note_repository.get(note.id)

    assert result is not None
    assert result.tags == [beta, alpha]
