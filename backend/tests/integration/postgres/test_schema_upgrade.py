from typing import cast

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.sqlalchemy.migrations import alembic_config
from adapters.out.sqlalchemy.schema_upgrade import (
    SchemaUpgradeRefused,
    read_schema_state,
    upgrade_schema,
)

pytestmark = pytest.mark.postgres


def _upgrade_by_one_revision(connection: Connection, config: Config) -> None:
    config.attributes["connection"] = connection
    command.upgrade(config, "+1")


async def test_upgrade_schema_brings_an_empty_database_to_head_with_the_vector_extension(  # noqa: E501
    unmigrated_engine: AsyncEngine,
) -> None:
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()

    state = await upgrade_schema(unmigrated_engine)

    assert state.current == head
    assert state.is_current
    async with unmigrated_engine.connect() as connection:
        extension = cast(
            str | None,
            await connection.scalar(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            ),
        )
    assert extension == "vector"


async def test_upgrade_schema_brings_a_database_one_revision_past_base_to_head(
    unmigrated_engine: AsyncEngine,
) -> None:
    async with unmigrated_engine.begin() as connection:
        await connection.run_sync(_upgrade_by_one_revision, alembic_config())
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()

    state = await upgrade_schema(unmigrated_engine)

    assert state.current == head
    assert state.is_current


async def test_read_schema_state_refuses_a_database_whose_revision_this_checkout_does_not_know_and_leaves_it_unchanged(  # noqa: E501
    unmigrated_engine: AsyncEngine,
) -> None:
    fabricated_revision = "0" * 12
    async with unmigrated_engine.begin() as connection:
        _ = await connection.execute(
            text(
                "CREATE TABLE alembic_version "
                + "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        _ = await connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
            {"rev": fabricated_revision},
        )

    with pytest.raises(SchemaUpgradeRefused):
        _ = await read_schema_state(unmigrated_engine)

    async with unmigrated_engine.connect() as connection:
        rows = (
            await connection.execute(text("SELECT version_num FROM alembic_version"))
        ).fetchall()
    assert rows == [(fabricated_revision,)]
