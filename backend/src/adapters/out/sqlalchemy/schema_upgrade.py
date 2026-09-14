from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError

from adapters.out.sqlalchemy.migrations import alembic_config, upgrade_to_head
from sqlalchemy import text
from sqlalchemy.engine import URL, Connection, make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

_ACCEPTED_DRIVERNAMES = {"postgres", "postgresql", "postgresql+asyncpg"}
_DROPPED_QUERY_PARAMS = {"channel_binding"}
_RENAMED_QUERY_PARAMS = {"sslmode": "ssl"}


class SchemaUpgradeRefused(Exception):
    """Neon schema upgrade refused before changing the database."""


def direct_asyncpg_url(raw: str) -> URL:
    url = make_url(raw)
    if url.drivername not in _ACCEPTED_DRIVERNAMES:
        raise SchemaUpgradeRefused(
            f"not a Postgres connection string: unsupported scheme {url.drivername!r}"
        )
    if not url.database:
        raise SchemaUpgradeRefused("connection string has no database name")
    if _is_pooler_host(url.host):
        raise SchemaUpgradeRefused(
            "refusing a pooler connection string; use Neon's direct "
            + "connection string instead"
        )
    return url.set(drivername="postgresql+asyncpg", query=_normalized_query(url.query))


@dataclass(frozen=True)
class SchemaState:
    database: str
    current: str | None
    head: str

    @property
    def is_current(self) -> bool:
        return self.current == self.head


async def read_schema_state(engine: AsyncEngine) -> SchemaState:
    script = ScriptDirectory.from_config(alembic_config())
    head = script.get_current_head()
    if head is None:
        raise SchemaUpgradeRefused("this checkout carries no migrations")

    async with engine.connect() as connection:
        current = await connection.run_sync(_current_revision)
        if current is None:
            if await _has_existing_tables(connection):
                raise SchemaUpgradeRefused(
                    "database has tables but no alembic_version; refusing an "
                    + "unmanaged database"
                )
        elif not _known_revision(script, current):
            raise SchemaUpgradeRefused(
                f"database is at revision {current!r}, which this checkout's "
                + "migration history does not know"
            )

    return SchemaState(database=engine.url.database or "", current=current, head=head)


async def upgrade_schema(engine: AsyncEngine) -> SchemaState:
    state = await read_schema_state(engine)
    if not state.is_current:
        await upgrade_to_head(engine)
        state = await read_schema_state(engine)
    return state


def _is_pooler_host(host: str | None) -> bool:
    if not host:
        return False
    return host.split(".", 1)[0].endswith("-pooler")


def _normalized_query(
    query: Mapping[str, str | Sequence[str]],
) -> dict[str, str | Sequence[str]]:
    normalized: dict[str, str | Sequence[str]] = {}
    for key, value in query.items():
        if key in _DROPPED_QUERY_PARAMS:
            continue
        normalized[_RENAMED_QUERY_PARAMS.get(key, key)] = value
    return normalized


def _current_revision(connection: Connection) -> str | None:
    context = MigrationContext.configure(connection)
    return context.get_current_revision()


def _known_revision(script: ScriptDirectory, revision: str) -> bool:
    try:
        _ = script.get_revision(revision)
    except CommandError:
        return False
    return True


async def _has_existing_tables(connection: AsyncConnection) -> bool:
    result = cast(
        bool,
        await connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_tables "
                + "WHERE schemaname = current_schema())"
            )
        ),
    )
    return result
