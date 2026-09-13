from typing import cast

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.sqlalchemy.engine import create_session_factory
from adapters.out.sqlalchemy.migrations import alembic_config, upgrade_to_head

pytestmark = pytest.mark.postgres


async def _alembic_version_rows(engine: AsyncEngine) -> list[object]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT version_num FROM alembic_version")
        )
        return list(result.fetchall())


async def test_upgrading_fresh_database_stamps_alembic_version_at_head(
    engine: AsyncEngine,
) -> None:
    async with engine.connect() as connection:
        table = cast(
            str | None,
            await connection.scalar(
                text("SELECT to_regclass('public.alembic_version')")
            ),
        )
    assert table == "alembic_version"
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    assert await _alembic_version_rows(engine) == [(head,)]


async def test_upgrading_already_migrated_database_leaves_revision_unchanged(
    engine: AsyncEngine,
) -> None:
    before = await _alembic_version_rows(engine)
    await upgrade_to_head(engine)
    after = await _alembic_version_rows(engine)
    assert after == before


async def test_session_from_create_session_factory_reads_alembic_version(
    engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        table = cast(
            str | None,
            await session.scalar(text("SELECT to_regclass('public.alembic_version')")),
        )
    assert table == "alembic_version"


async def test_server_offers_vector_extension_in_pg_available_extensions(
    engine: AsyncEngine,
) -> None:
    async with engine.connect() as connection:
        name = cast(
            str | None,
            await connection.scalar(
                text("SELECT name FROM pg_available_extensions WHERE name = 'vector'")
            ),
        )
    assert name == "vector"
