from alembic.config import Config

from sqlalchemy.ext.asyncio import AsyncEngine


def alembic_config() -> Config:
    raise NotImplementedError


async def upgrade_to_head(_engine: AsyncEngine) -> None:
    raise NotImplementedError
