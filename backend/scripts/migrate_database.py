"""Bring a Neon database to the schema this checkout expects.

Reads Neon's direct connection string from `NEON_DIRECT_URL` (never from `.env`),
shows the current and head revisions, asks for the database name, and applies
every pending Alembic revision in one transaction. A database already at head
exits without prompting; pooler URLs and unmanaged databases are refused.

Usage:
    cd backend && NEON_DIRECT_URL=... uv run python scripts/migrate_database.py [--yes]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass

from sqlalchemy.engine import URL

from adapters.out.sqlalchemy.engine import create_engine
from adapters.out.sqlalchemy.schema_upgrade import (
    SchemaState,
    SchemaUpgradeRefused,
    direct_asyncpg_url,
    read_schema_state,
    upgrade_schema,
)

_DESCRIPTION = "Bring a Neon database to this checkout's schema."
_URL_VARIABLE = "NEON_DIRECT_URL"


@dataclass(frozen=True)
class _Args:
    yes: bool


def main() -> None:
    args = _parse_args()
    raw_url = os.environ.get(_URL_VARIABLE, "")
    if not raw_url:
        print(f"{_URL_VARIABLE} is not set", file=sys.stderr)
        sys.exit(1)

    try:
        url = direct_asyncpg_url(raw_url)
        print(f"database: {url.render_as_string(hide_password=True)}")
        asyncio.run(_migrate(url, yes=args.yes))
    except SchemaUpgradeRefused as refused:
        print(str(refused), file=sys.stderr)
        sys.exit(1)


async def _migrate(url: URL, *, yes: bool) -> None:
    engine = create_engine(url.render_as_string(hide_password=False))
    try:
        state = await read_schema_state(engine)
        print(f"schema: {_describe(state)} → {state.head}")
        if state.is_current:
            print(f"already at {state.head}, nothing to do")
            return
        if not yes and not _confirmed(state.database):
            print("aborted, nothing was changed")
            sys.exit(1)

        upgraded = await upgrade_schema(engine)
        print(f"upgraded to {upgraded.head}")
    finally:
        await engine.dispose()


def _describe(state: SchemaState) -> str:
    return state.current if state.current is not None else "empty"


def _confirmed(database_name: str) -> bool:
    answer = input(f"type the database name ({database_name}) to upgrade it: ")
    return answer.strip() == database_name


def _parse_args() -> _Args:
    parser = argparse.ArgumentParser(description=_DESCRIPTION)
    _ = parser.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt"
    )
    namespace = parser.parse_args()
    return _Args(yes=bool(namespace.yes))  # pyright: ignore[reportAny]


if __name__ == "__main__":
    main()
