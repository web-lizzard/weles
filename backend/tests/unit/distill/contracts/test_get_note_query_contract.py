from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from adapters.out.in_memory.distill.get_note_query import InMemoryGetNoteQueryAdapter
from adapters.out.in_memory.distill.note_repository import InMemoryNoteRepository
from adapters.out.sqlalchemy.distill.get_note_query import SqlAlchemyGetNoteQueryAdapter
from adapters.out.sqlalchemy.distill.note_repository import SqlAlchemyNoteRepository
from adapters.out.sqlalchemy.engine import create_session_factory
from application.distill.queries.get_note import GetNoteQueryPort
from domain.distill.exceptions import DistillNoteNotFoundError
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

_CALLER = UserId.new()


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


@dataclass
class _GetNoteFixture:
    query: GetNoteQueryPort
    notes: NoteRepository


def _note(
    status: DistillationStatus,
    at: datetime,
    *,
    owner_id: UserId | None = None,
) -> Note:
    return Note(
        id=NoteId(value=uuid4()),
        owner_id=owner_id or _CALLER,
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value="We discussed how connections are established."),
        tags=[TagSnapshot(id=uuid4(), label="networking")],
        distillation_status=status,
        approved_at=at,
        created_at=at,
        updated_at=at,
    )


@pytest.fixture(
    params=["in_memory", pytest.param("postgres", marks=pytest.mark.postgres)]
)
def get_note_fixture(request: pytest.FixtureRequest) -> _GetNoteFixture:
    if request.param == "in_memory":  # pyright: ignore[reportAny]
        notes = InMemoryNoteRepository()
        query: GetNoteQueryPort = InMemoryGetNoteQueryAdapter(notes)
        return _GetNoteFixture(query, notes)
    engine: AsyncEngine = request.getfixturevalue("engine")  # pyright: ignore[reportAny]
    session_factory = create_session_factory(engine)
    notes = _CommittingNoteRepository(session_factory)
    return _GetNoteFixture(
        cast(
            GetNoteQueryPort,
            cast(object, SqlAlchemyGetNoteQueryAdapter(session_factory)),
        ),
        notes,
    )


async def test_get_note_maps_full_note_shape_into_the_detail_dto(
    get_note_fixture: _GetNoteFixture,
) -> None:
    now = datetime.now(UTC)
    note = _note(DistillationStatus.READY, now)
    await get_note_fixture.notes.save(note)

    result = await get_note_fixture.query.get_note(_CALLER, note.id)

    assert result.note_id == note.id.value
    assert result.topic.id == note.topic.id
    assert result.topic.label == note.topic.label
    assert result.content == note.content.value
    assert [(tag.id, tag.label) for tag in result.tags] == [
        (t.id, t.label) for t in note.tags
    ]
    assert result.distillation_status == "ready"
    assert result.approved_at == note.approved_at
    assert result.created_at == note.created_at
    assert result.updated_at == note.updated_at


async def test_get_note_returns_tags_in_the_order_they_were_saved(
    get_note_fixture: _GetNoteFixture,
) -> None:
    stamped_at = datetime.now(UTC)
    alpha = TagSnapshot(id=uuid4(), label="alpha")
    beta = TagSnapshot(id=uuid4(), label="beta")
    note = Note(
        id=NoteId(value=uuid4()),
        owner_id=_CALLER,
        session_id=SessionId(value=uuid4()),
        topic=TopicSnapshot(id=uuid4(), label="TCP handshakes"),
        content=NoteContent(value="Body text."),
        tags=[alpha, beta],
        distillation_status=DistillationStatus.READY,
        approved_at=stamped_at,
        created_at=stamped_at,
        updated_at=stamped_at,
    )
    await get_note_fixture.notes.save(note)

    result = await get_note_fixture.query.get_note(_CALLER, note.id)

    assert [(tag.id, tag.label) for tag in result.tags] == [
        (alpha.id, alpha.label),
        (beta.id, beta.label),
    ]


async def test_get_note_raises_not_found_for_an_unknown_note_id(
    get_note_fixture: _GetNoteFixture,
) -> None:
    with pytest.raises(DistillNoteNotFoundError):
        _ = await get_note_fixture.query.get_note(UserId.new(), NoteId(value=uuid4()))


@pytest.mark.parametrize(
    "status",
    [
        DistillationStatus.GENERATING,
        DistillationStatus.READY,
        DistillationStatus.FAILED,
    ],
)
async def test_get_note_exposes_raw_distillation_status(
    get_note_fixture: _GetNoteFixture,
    status: DistillationStatus,
) -> None:
    note = _note(status, datetime.now(UTC))
    await get_note_fixture.notes.save(note)

    result = await get_note_fixture.query.get_note(_CALLER, note.id)

    assert result.distillation_status == status.value


async def test_get_note_raises_not_found_when_note_belongs_to_another_owner(
    get_note_fixture: _GetNoteFixture,
) -> None:
    note_owner = UserId.new()
    caller = UserId.new()
    note = _note(DistillationStatus.READY, datetime.now(UTC), owner_id=note_owner)
    await get_note_fixture.notes.save(note)

    with pytest.raises(DistillNoteNotFoundError):
        _ = await get_note_fixture.query.get_note(caller, note.id)
