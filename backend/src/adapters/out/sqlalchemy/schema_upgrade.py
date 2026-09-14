from dataclasses import dataclass

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine


class SchemaUpgradeRefused(Exception):
    """Neon schema upgrade refused before changing the database."""


def direct_asyncpg_url(raw: str) -> URL:
    _ = raw
    raise NotImplementedError


@dataclass(frozen=True)
class SchemaState:
    database: str
    current: str | None
    head: str

    @property
    def is_current(self) -> bool:
        raise NotImplementedError


async def read_schema_state(engine: AsyncEngine) -> SchemaState:
    _ = engine
    raise NotImplementedError


async def upgrade_schema(engine: AsyncEngine) -> SchemaState:
    _ = engine
    raise NotImplementedError
