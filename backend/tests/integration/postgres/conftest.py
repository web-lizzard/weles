import asyncio
import os
from collections.abc import AsyncIterator
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from adapters.out.sqlalchemy.engine import create_engine
from adapters.out.sqlalchemy.migrations import upgrade_to_head


def _resolved_test_database_url() -> str:
    raw = os.environ.get("TEST_DATABASE_URL")
    if not raw:
        pytest.fail(
            "TEST_DATABASE_URL is not set; run postgres tests only when it is "
            + "available or exclude them with -m 'not postgres'"
        )
    test_url = make_url(raw)
    database_url = os.environ.get("DATABASE_URL")
    if database_url and test_url.database:
        return (
            make_url(database_url)
            .set(database=test_url.database)
            .render_as_string(hide_password=False)
        )
    return raw


def _maintenance_database_url(test_url: str) -> str:
    url = make_url(test_url)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        maintenance_db = make_url(database_url).database
        if maintenance_db:
            return url.set(database=maintenance_db).render_as_string(
                hide_password=False
            )
    return url.set(database="postgres").render_as_string(hide_password=False)


async def _recreate_database_and_migrate(test_url: str) -> None:
    url = make_url(test_url)
    database_name = url.database
    if not database_name:
        pytest.fail(f"TEST_DATABASE_URL must include a database name: {test_url}")

    maintenance_engine = create_engine(_maintenance_database_url(test_url))
    try:
        async with maintenance_engine.execution_options(
            isolation_level="AUTOCOMMIT"
        ).connect() as connection:
            _ = await connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    + "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": database_name},
            )
            _ = await connection.execute(
                text(f'DROP DATABASE IF EXISTS "{database_name}"')
            )
            _ = await connection.execute(
                text(f'CREATE DATABASE "{database_name}" TEMPLATE template0')
            )
    finally:
        await maintenance_engine.dispose()

    app_engine = create_engine(test_url)
    try:
        await upgrade_to_head(app_engine)
    finally:
        await app_engine.dispose()


@pytest.fixture(scope="session")
def migrated_database_url() -> str:
    test_url = _resolved_test_database_url()
    try:
        asyncio.run(_recreate_database_and_migrate(test_url))
    except Exception as exc:
        pytest.fail(
            f"Postgres setup failed for {test_url!r}; "
            + f"use -m 'not postgres' to skip: {exc}"
        )
    return test_url


@pytest.fixture
async def engine(migrated_database_url: str) -> AsyncIterator[AsyncEngine]:
    db_engine = create_engine(migrated_database_url)
    try:
        yield db_engine
    finally:
        async with db_engine.begin() as connection:
            result = await connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    + "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
                )
            )
            tables = [cast(str, row[0]) for row in result.fetchall()]
            if tables:
                quoted = ", ".join(f'"{name}"' for name in tables)
                _ = await connection.execute(
                    text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE")
                )
        await db_engine.dispose()
