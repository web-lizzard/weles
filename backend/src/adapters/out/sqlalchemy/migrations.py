from pathlib import Path

from alembic import command
from alembic.config import Config

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine


def alembic_config() -> Config:
    ini_path = Path(__file__).resolve().parent / "alembic.ini"
    return Config(str(ini_path))


def _upgrade_on_connection(connection: Connection, config: Config) -> None:
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


async def upgrade_to_head(engine: AsyncEngine) -> None:
    config = alembic_config()
    async with engine.begin() as connection:
        await connection.run_sync(_upgrade_on_connection, config)
