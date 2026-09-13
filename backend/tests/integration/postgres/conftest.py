from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.fixture(scope="session")
def migrated_database_url() -> str:
    raise NotImplementedError


@pytest.fixture
async def engine(_migrated_database_url: str) -> AsyncIterator[AsyncEngine]:
    raise NotImplementedError
