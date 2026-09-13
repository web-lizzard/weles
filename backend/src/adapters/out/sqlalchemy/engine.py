from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def create_engine(_url: str) -> AsyncEngine:
    raise NotImplementedError


def create_session_factory(
    _engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    raise NotImplementedError
