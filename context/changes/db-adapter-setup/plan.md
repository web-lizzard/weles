# Local Postgres Tooling and MCP Access — Implementation Plan

Execution state lives in `todos.md` (sibling of this file), per the `/plan` skill's `references/todos-format.md`.

## Overview

Give the `db-adapter` effort a place to stand before any domain table exists: the dev
Postgres runs with pgvector available, the author can query it read-only through a Postgres
MCP server, and the backend carries a SQLAlchemy adapter package with the async engine and
session source plus a self-contained Alembic environment that upgrades an empty revision
history cleanly. A handful of integration tests prove that path against a real Postgres, shaped
so a future GitHub Actions job can run them against a service container unchanged. This is
slice S-01 of effort `db-adapter` and delivers FR-09.

## Current State Analysis

- `.devcontainer/docker-compose.yml` already runs a `postgres` service on `postgres:16`
  (healthchecked; the `app` service `depends_on` it) and sets
  `DATABASE_URL=postgresql+asyncpg://weles:weles@postgres:5432/weles` on `app`. Probed from the
  container: PostgreSQL 16.13, and `pg_available_extensions` has **no** `vector` row.
- `backend/pyproject.toml:10-12` already depends on `sqlalchemy[asyncio]` (2.0.52 installed),
  `asyncpg` (0.31.0) and `alembic` (1.19.1). No engine, model, or Alembic environment exists
  under `backend/src/`.
- `backend/src/adapters/db/__init__.py` is an empty stub nothing imports; the layering rule
  names `adapters/out/sqlalchemy/` as the SQL adapter home
  (`context/foundation/rules/layering.md`).
- `Settings.database_url` is required (`backend/src/config/settings.py:30`) and is read at import
  time by `adapters/compose.py:103` and `main.py:17`, but nothing consumes it yet.
- `.mcp.json` holds only the `langfuse` HTTP server. The container has `uvx` and `npx`, no
  `docker` CLI and no `psql`.
- No test touches a database. Integration tests live in `backend/tests/integration/`, whose
  `conftest.py` imports `main` (so `DATABASE_URL` must be set to collect them).

## Desired End State

The devcontainer's Postgres is `pgvector/pgvector:pg16` and offers the `vector` extension. From
an agent session, the `postgres` MCP server answers a query against the local `weles` database
in restricted (read-only) mode. `backend/src/adapters/out/sqlalchemy/` owns `create_engine`,
`create_session_factory`, `upgrade_to_head`, `alembic.ini` and `migrations/` with an empty
`versions/`. `alembic -c src/adapters/out/sqlalchemy/alembic.ini upgrade head` succeeds on the
dev database. Tests marked `postgres` recreate `weles_test` once per session, migrate it through
the same Alembic environment, and pass; everything else passes under `-m 'not postgres'`.

Verify: `cd backend && uv run pytest` green (Postgres suite included), `uv run basedpyright`
and `uv run ruff check src tests` clean, and the Manual rows of Phases 1 and 3.

### Key Discoveries:
- An `alembic upgrade head` with zero revisions still creates the `alembic_version` table
  (probed against the compose Postgres) — the empty-history outcome is observable without a
  baseline revision.
- `uvx postgres-mcp` (0.3.0) crashes at import against `mcp` 2.x (`mcp.server.fastmcp` was
  renamed); `uvx --with 'mcp<2' postgres-mcp==0.3.0` starts and exposes
  `--access-mode {unrestricted,restricted}` and a `DATABASE_URI` env / positional URL.
- The `async` Alembic template's `env.py` calls `asyncio.run(...)` and `fileConfig(...)`
  unconditionally; both break when Alembic is driven from inside pytest (see Critical
  Implementation Details).
- `Settings` uses `extra="forbid"` only against the `.env` file; a `TEST_DATABASE_URL` process
  environment variable does not trip it, so the test URL stays out of `Settings` entirely.
- `pytest-asyncio` 1.4.0 with `asyncio_mode = "auto"` runs each async test on a function-scoped
  loop; asyncpg connections are bound to the loop that opened them.
- `context/foundation/testing-conventions.md` is authored only by `/testing-shape`; the new
  `postgres` marker and test folder are recorded there by that skill, not by this change.

## What We're NOT Doing

- No GitHub Actions workflow. The test shape is designed for one (env-var URL, marker
  selection, fixture-created database, no compose-only init scripts), but CI is not built here.
- No `CREATE EXTENSION vector` and no Alembic revision. The extension is enabled by the first
  revision that uses it; this change only makes it available on the server.
- No ORM models, tables, mappers, repositories, or `UnitOfWork` implementation (S-02 onward).
- No wiring of the engine into `adapters/compose.py` or `main.py` — the runtime switch is S-06.
- No `pgvector` Python package.
- No edit to `context/foundation/testing-conventions.md`.

## Implementation Approach

Infra first, because every later phase needs the pgvector image and `TEST_DATABASE_URL` in the
container environment, and the MCP server is the slice's own demonstrable outcome. Then the
adapter package and test fixtures as stubs, so the behaviour phase's tests import real symbols
and fail on `NotImplementedError` rather than on import. The behaviour phase fills the engine,
session factory, Alembic bridge, `env.py`, and fixtures until the Postgres suite is green.

Alembic lives wholly inside the adapter package, `alembic.ini` included; the CLI is invoked
with `-c`. `env.py` supports two entry paths: the CLI (it builds its own async engine from
`Settings().database_url`) and programmatic use from `upgrade_to_head`, which hands `env.py` an
already-open sync connection through `config.attributes`.

## Critical Implementation Details

`upgrade_to_head` is awaited from code that already runs on an event loop, so `env.py` must not
call `asyncio.run` on that path. `upgrade_to_head` opens a connection on the given engine and
runs `command.upgrade` inside `connection.run_sync`, placing the sync connection in
`config.attributes["connection"]`. `env.py` migrates on that connection when present, and falls
back to `asyncio.run(run_async_migrations())` only on the CLI path.

`env.py` must skip `fileConfig(...)` on the programmatic path. Otherwise the first Postgres test
reconfigures the root logger and silences pytest's log capture for the rest of the session.

The session fixture that recreates `weles_test` is **synchronous** and drives its async work with
`asyncio.run`, while the per-test engine fixture is async and function-scoped. A session-scoped
async engine would hand asyncpg connections opened on one loop to tests running on another.
`CREATE DATABASE` / `DROP DATABASE` cannot run inside a transaction, so they go through an
engine on the `postgres` maintenance database with `isolation_level="AUTOCOMMIT"`.

## Phase 1: Local Postgres with pgvector and MCP access

### Overview

The dev Postgres gains pgvector, the container environment gains the test database URL, and the
author can query the dev database from an agent session.

### Changes Required:

#### 1. Compose Postgres image and test URL

**File**: `.devcontainer/docker-compose.yml`

**Intent**: Make the `vector` extension available on the dev server without touching the
existing data volume, and give the `app` container the URL the Postgres test fixtures read — the
same variable a CI job will set.

**Contract**: `postgres.image: pgvector/pgvector:pg16` (same major as today's `postgres:16`, so
`postgres-data` is reused as is). `app.environment` gains
`TEST_DATABASE_URL: postgresql+asyncpg://weles:weles@postgres:5432/weles_test`. Healthcheck,
credentials, and `DATABASE_URL` unchanged.

#### 2. Postgres MCP server

**File**: `.mcp.json`

**Intent**: FR-09 — the author queries local rows from an agent session, with writes refused by
the server rather than by discipline.

**Contract**: a `postgres` entry beside `langfuse`: `type: stdio`, `command: uvx`,
`args: ["--with", "mcp<2", "postgres-mcp==0.3.0", "--access-mode=restricted"]`,
`env: { "DATABASE_URI": "postgresql://weles:weles@postgres:5432/weles" }`. The URI is plain
libpq form (no `+asyncpg`); the `mcp<2` pin is required, not cosmetic.

### Success Criteria:

#### Automated Verification:
- `python3 -m json.tool .mcp.json` exits 0
- `uvx --with 'mcp<2' postgres-mcp==0.3.0 --help` exits 0 and lists `--access-mode`

#### Manual Verification:
- On the host, rebuild the devcontainer; then in the container `echo $TEST_DATABASE_URL`
  prints the `weles_test` URL, and
  `select name, default_version from pg_available_extensions where name = 'vector'` on `weles`
  returns one row
- In a fresh agent session, the `postgres` MCP server is listed as connected and answers
  `select current_database(), version()` with `weles` and PostgreSQL 16; an `insert` attempted
  through it is refused

---

## Phase 2: SQLAlchemy adapter and Alembic environment stubs

### Overview

Materialize every symbol and file the Postgres tests import or rely on, with no behaviour.

### Changes Required:

#### 1. Adapter package and retired stub

**File**: `backend/src/adapters/out/sqlalchemy/__init__.py`, `backend/src/adapters/db/__init__.py` (deleted)

**Intent**: Put the SQL adapter where the layering rule says adapters live, and remove the empty
`adapters/db` stub so there is one obvious home.

**Contract**: empty package `adapters.out.sqlalchemy`; `adapters/db/` removed.

#### 2. Engine and session source

**File**: `backend/src/adapters/out/sqlalchemy/engine.py`

**Intent**: The single place an async engine and session factory are built, for tests now and
for the runtime composition in S-06.

**Contract**: `def create_engine(url: str) -> AsyncEngine` and
`def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]`
(the factory is built with `expire_on_commit=False`, per the effort research). Bodies raise
`NotImplementedError`.

#### 3. Alembic bridge

**File**: `backend/src/adapters/out/sqlalchemy/migrations.py`

**Intent**: Let code outside the CLI run the package's migrations without knowing where the
Alembic environment sits on disk.

**Contract**: `def alembic_config() -> Config` — a `Config` bound to the package's own
`alembic.ini`. `async def upgrade_to_head(engine: AsyncEngine) -> None` — migrates the database
behind `engine` to `head`. Bodies raise `NotImplementedError`.

#### 4. Alembic environment

**File**: `backend/src/adapters/out/sqlalchemy/alembic.ini`, `backend/src/adapters/out/sqlalchemy/migrations/env.py`, `backend/src/adapters/out/sqlalchemy/migrations/script.py.mako`, `backend/src/adapters/out/sqlalchemy/migrations/versions/.gitkeep`

**Intent**: The whole Alembic environment lives inside the adapter, with no revision yet.

**Contract**: `alembic.ini` from the `async` template with `script_location = %(here)s/migrations`,
`prepend_sys_path = %(here)s/../../..` (resolves to `backend/src`, so the CLI works without
`PYTHONPATH`), `path_separator = os`, and **no** `sqlalchemy.url`. `script.py.mako` from the
template. `env.py` is the template, left as generated in this phase; `target_metadata = None`.

#### 5. Postgres marker

**File**: `backend/pyproject.toml`

**Intent**: One selector for the database tests, locally and in a future CI job.

**Contract**: `[tool.pytest.ini_options] markers` gains
`"postgres: needs a reachable Postgres at TEST_DATABASE_URL"`.

#### 6. Postgres test fixtures

**File**: `backend/tests/integration/postgres/__init__.py`, `backend/tests/integration/postgres/conftest.py`

**Intent**: The database fixtures every later slice's Postgres tests stand on.

**Contract**:
- `migrated_database_url` — session-scoped, **sync** fixture returning the `TEST_DATABASE_URL`
  value after the database behind it has been dropped if present, created, and upgraded to
  `head` through `upgrade_to_head`. Missing `TEST_DATABASE_URL`, or a Postgres that refuses the
  connection, is `pytest.fail` with a message naming the URL and `-m 'not postgres'`.
- `engine` — function-scoped async fixture yielding `create_engine(migrated_database_url)`;
  after the test it truncates every table in `public` except `alembic_version`
  (`TRUNCATE … RESTART IDENTITY CASCADE`, a no-op while there are none) and disposes the engine.

Bodies raise `NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes

---

## Phase 3: Postgres engine, session source and empty-history migration

### Overview

Fill the engine, session factory, Alembic bridge, `env.py` dual path and fixtures until the
database suite is green.

### Changes Required:

#### 1. Engine and session source

**File**: `backend/src/adapters/out/sqlalchemy/engine.py`

**Intent**: Build a real async engine and a session factory that yields usable sessions.

**Contract**: as Phase 2. `create_engine` wraps SQLAlchemy's `create_async_engine(url)`;
`create_session_factory` returns `async_sessionmaker(engine, expire_on_commit=False)`.

#### 2. Alembic bridge

**File**: `backend/src/adapters/out/sqlalchemy/migrations.py`

**Intent**: Migrate a database from inside a running event loop.

**Contract**: `alembic_config` resolves `alembic.ini` relative to the module file.
`upgrade_to_head` opens `engine.begin()` and runs `command.upgrade(config, "head")` inside
`run_sync`, with the sync connection placed in `config.attributes["connection"]`.

#### 3. Dual-path `env.py`

**File**: `backend/src/adapters/out/sqlalchemy/migrations/env.py`

**Intent**: One environment serving both the CLI and programmatic callers.

**Contract**: when `config.attributes` carries `connection`, configure the context on it and run
migrations synchronously, without `fileConfig`. Otherwise call `fileConfig`, build the async
engine from `Settings().database_url` (`NullPool`), and `asyncio.run` the migrations. Offline
mode reads the same URL.

#### 4. Postgres test fixtures

**File**: `backend/tests/integration/postgres/conftest.py`

**Intent**: Implement the fixture contract from Phase 2.

**Contract**: as Phase 2; database drop/create goes through an AUTOCOMMIT engine on the
`postgres` maintenance database of the same server.

#### 5. Postgres integration tests

**File**: `backend/tests/integration/postgres/test_database_tooling.py`

**Intent**: Prove the setup slice's outcome on a real Postgres.

**Contract**: module-level `pytestmark = pytest.mark.postgres`; every test takes `engine`.

#### Tests

- upgrading a freshly created database to head leaves an `alembic_version` table with no applied
  revision;
- upgrading an already-migrated database to head again leaves its revision state unchanged;
- a session from `create_session_factory` reads the migrated database's `alembic_version`;
- the server offers the `vector` extension in `pg_available_extensions`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest -m postgres -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

#### Manual Verification:
- `cd backend && uv run alembic -c src/adapters/out/sqlalchemy/alembic.ini upgrade head`
  exits 0 on the dev database, and
  `uv run alembic -c src/adapters/out/sqlalchemy/alembic.ini current` prints no revision
- Ask the `postgres` MCP server for `select to_regclass('alembic_version')` on `weles` — it
  returns `alembic_version`

---

## Testing Strategy

### Unit Tests:

None. Every observable outcome here is a property of a real Postgres; a unit test would restate
the SQLAlchemy calls.

### Integration Tests:

Four tests in `backend/tests/integration/postgres/`, marked `postgres`, against `weles_test`.
Each session drops and recreates that database and migrates it through the adapter's own Alembic
environment, so an upgrade from empty runs on every invocation. Tests run on real commits; the
`engine` fixture truncates tables afterwards. That keeps later atomicity tests (FR-07) honest,
which a rollback-wrapped test transaction would not. The suite stays deliberately small; later
slices add only their most important Postgres cases.

Future CI (not built here): a job with a `pgvector/pgvector:pg16` service, `TEST_DATABASE_URL`
pointing at it, and `uv run pytest -m postgres`; other jobs run `-m 'not postgres'`. Nothing in
the fixtures depends on compose hostnames or init scripts.

### Manual Testing Steps:

1. Rebuild the devcontainer on the host.
2. In an agent session, query the dev database through the `postgres` MCP server.
3. Run the Alembic CLI through the adapter's `alembic.ini` against the dev database.

## Performance Considerations

None: one database recreate per test session and a `TRUNCATE` per Postgres test.

## Migration Notes

Switching the compose image from `postgres:16` to `pgvector/pgvector:pg16` keeps the same
Postgres major and data directory layout, so the `postgres-data` volume is reused without a dump
or restore. The dev database gets an `alembic_version` table from the Phase 3 manual upgrade.

## References

- `context/efforts/db-adapter/frame.md` — FR-09 and effort boundaries
- `context/efforts/db-adapter/roadmap.md` — slice S-01
- `context/efforts/db-adapter/research-sql-alchemy.md` — async engine and session guidance
- `context/efforts/db-adapter/frame-log.md` — parked: test database choice, pgvector vs array
- `context/efforts/deployment/research.md` — Neon supports pgvector; direct URL for migrations
- `context/foundation/rules/layering.md` — `adapters/out/sqlalchemy/`
- <https://alembic.sqlalchemy.org/en/latest/cookbook.html> — programmatic use with asyncio, connection sharing
- <https://github.com/crystaldba/postgres-mcp> — `postgres-mcp` access modes
- <https://hub.docker.com/r/pgvector/pgvector/tags> — `pg16` tags
