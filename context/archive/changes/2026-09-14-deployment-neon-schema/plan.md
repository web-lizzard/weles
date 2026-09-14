# Neon Schema Script Implementation Plan

Execution state lives in `todos.md` (sibling of this file); this plan carries no checkboxes.

## Overview

The author needs one supported script that brings the hosted instance's Neon database, empty or behind, to the schema the checked-out commit expects, `vector` extension included (deployment FR-08, roadmap slice S-04). The script reuses the existing Alembic history. It adds a Neon-safe connection path, a readable preview of the upgrade with a confirmation, and clear refusals for databases it must not touch.

## Current State Analysis

Alembic revisions already live in `backend/src/adapters/out/sqlalchemy/migrations/versions/`. Test support applies them through `upgrade_to_head(engine)`. Nothing lets the author point that mechanism at a remote database. The app does not migrate on startup.

The obvious route of running `alembic upgrade head` with Neon's connection string fails in three ways:

- `migrations/env.py` resolves its URL through `Settings()`. That requires `AUTH_SIGNING_SECRET` and reads the local `backend/.env`, so it would target the local database, not Neon.
- Neon hands out `postgresql://…?sslmode=require&channel_binding=require`. SQLAlchemy's asyncpg dialect forwards URL query params as `asyncpg.connect()` kwargs, and asyncpg accepts neither `sslmode` nor `channel_binding` as kwargs, so the connection dies with `TypeError`.
- Neon's `-pooler` host runs PgBouncer in transaction mode, which is unsuitable for DDL. Migrations need the direct host (`research.md`, Pooling).

### Key Discoveries:

- `backend/src/adapters/out/sqlalchemy/migrations.py:20-23`: `upgrade_to_head` runs every pending revision inside one `engine.begin()` transaction, handing the connection to `env.py` via `config.attributes["connection"]`. That bypasses `Settings()`, and Postgres's transactional DDL rolls a failed upgrade back as a whole.
- `backend/src/adapters/out/sqlalchemy/migrations/env.py:52-55`: the `connection` attribute short-circuits URL resolution. This is the seam the script uses.
- `backend/src/adapters/out/sqlalchemy/migrations/versions/2ce37af2f0f8_create_capture_tables.py:25`: the first revision already runs `CREATE EXTENSION IF NOT EXISTS vector`, so an empty Neon database gets `vector` with no extra step.
- `.venv/.../sqlalchemy/dialects/postgresql/asyncpg.py:1133-1137` (SQLAlchemy 2.0.52): `opts.update(url.query)` passes query params straight to `asyncpg.connect`, which takes `ssl=`, not `sslmode=`.
- `backend/src/config/settings.py:38-42`: `Settings` uses `env_file=".env"` with `extra="forbid"`. A `NEON_DIRECT_URL` line in `backend/.env` would break app startup, so the variable is set per invocation only.
- `backend/scripts/reset_database.py`: existing script pattern. It prints the target with the password hidden, asks the author to type the database name, supports `--yes`, and exits non-zero on abort.
- `backend/tests/integration/support/postgres.py:45-77`: pattern for creating a database through a maintenance connection, reusable for fresh per-test databases.

## Desired End State

From a checkout of the commit to deploy, the author runs:

```bash
cd backend && NEON_DIRECT_URL='<neon direct connection string>' uv run python scripts/migrate_database.py
```

The script prints the target (password hidden) and `current → head`, asks for the database name, upgrades, and reports the new revision. An up-to-date database exits 0 without prompting.

The script refuses and changes nothing when:

- the URL is a pooler URL;
- the URL has a non-Postgres scheme;
- the database records a revision this checkout does not know;
- the database holds tables with no `alembic_version`.

Verification: the `-m postgres` tests for `schema_upgrade` pass, and a manual run against an empty Neon branch reaches head with `vector` installed.

## What We're NOT Doing

- Moving data from a local database into Neon (frame out-of-scope).
- Guarding deploy/schema ordering. The author owns it; revisit before the next migration after this effort lands (frame out-of-scope).
- Downgrades or targeting a revision other than the checkout's head.
- Adding `NEON_DIRECT_URL` to `Settings` or pydantic validation (user decision).
- Migrating on app startup or from CI. S-05 may call the script later; nothing here wires it.
- Changing `migrations/env.py` or the Alembic CLI path.

## Implementation Approach

Keep the logic in a new SQLAlchemy adapter module, so tests import it `src`-rooted. `scripts/` is not on the test `pythonpath`. The module has three responsibilities:

- turn a Neon connection string into a direct asyncpg URL, or refuse it;
- read the database's schema state against the checkout's head, refusing unsafe databases;
- upgrade through the existing `upgrade_to_head`.

`backend/scripts/migrate_database.py` stays thin: it reads the environment variable, previews, confirms, calls the module, and maps a refusal to exit code 1. The refusal type is a plain adapter exception, not a `CoreException`: it never crosses the HTTP boundary, so it needs no `code → status` mapping.

## Critical Implementation Details

Normalize the URL before building the engine. Rewrite the scheme to `postgresql+asyncpg`, map `sslmode` → `ssl` with the same value, and drop `channel_binding`. Any leftover libpq-only query param raises `TypeError` inside asyncpg at connect time, not at URL parse time.

## Phase 1: Schema Upgrade Stubs

### Overview

Materialize the symbols the Phase 2 tests import, with unimplemented bodies.

### Changes Required:

#### 1. Schema upgrade adapter module

**File**: `backend/src/adapters/out/sqlalchemy/schema_upgrade.py`

**Intent**: Give the script and its tests one importable surface for URL handling, state reading, and upgrading.

**Contract**: Public symbols (bodies raise `NotImplementedError`), public before private:

- `class SchemaUpgradeRefused(Exception)`: carries a human-readable reason naming what was refused and why.
- `def direct_asyncpg_url(raw: str) -> sqlalchemy.engine.URL`
- `@dataclass(frozen=True) class SchemaState`: `database: str`, `current: str | None`, `head: str`, property `is_current: bool`.
- `async def read_schema_state(engine: AsyncEngine) -> SchemaState`
- `async def upgrade_schema(engine: AsyncEngine) -> SchemaState`

### Success Criteria:

#### Automated Verification:

- `cd backend && uv run basedpyright` passes.
- `cd backend && uv run pytest tests/unit` stays green.

---

## Phase 2: Schema Upgrade Behavior

### Overview

Implement Neon URL normalization, schema-state reading with refusals, and the upgrade to head.

### Changes Required:

#### 1. URL normalization

**File**: `backend/src/adapters/out/sqlalchemy/schema_upgrade.py`

**Intent**: Accept the connection string exactly as Neon's console shows it and produce a URL asyncpg can connect with, refusing anything that is not a direct Postgres URL.

**Contract**: `direct_asyncpg_url(raw)`:

- accepts `postgres://`, `postgresql://`, and `postgresql+asyncpg://`;
- returns drivername `postgresql+asyncpg`, with `sslmode` renamed to `ssl` (value kept) and `channel_binding` removed; other params are kept;
- raises `SchemaUpgradeRefused` for any other scheme, a missing database name, or a host whose first label ends in `-pooler`. The pooler message says to use the direct connection string.

#### 2. Schema state and upgrade

**File**: `backend/src/adapters/out/sqlalchemy/schema_upgrade.py`

**Intent**: Tell the author where the database stands relative to this checkout, and move it to head only when that is safe.

**Contract**:

- `read_schema_state(engine)` reads the current revision through Alembic's `MigrationContext` on a `run_sync` connection and takes `head` from `ScriptDirectory.from_config(alembic_config())`. It raises `SchemaUpgradeRefused` in two cases:
  - the current revision is not in this checkout's script directory (the database is ahead or on another history);
  - there is no `alembic_version` but tables already exist in `current_schema()`.
- `upgrade_schema(engine)` re-checks state, calls the existing `upgrade_to_head(engine)` when the database is not current, and returns the re-read state.
- A refused database is left byte-for-byte unchanged.

### Success Criteria:

#### Automated Verification:

- `cd backend && uv run pytest tests/unit/adapters/test_schema_upgrade.py -v` passes.
- `cd backend && uv run pytest tests/integration/postgres/test_schema_upgrade.py -m postgres -v` passes with `TEST_DATABASE_URL` set.
- `cd backend && uv run basedpyright` passes.
- `cd backend && uv run ruff check src tests` passes.

---

## Phase 3: Migration Script and Runbook

### Overview

Wrap the adapter in the author-facing script and document when to run it.

### Changes Required:

#### 1. Migration script

**File**: `backend/scripts/migrate_database.py`

**Intent**: One supported command that brings a Neon database to the checkout's schema, showing what it will do and asking before it does it.

**Contract**:

- Usage: `cd backend && NEON_DIRECT_URL=… uv run python scripts/migrate_database.py [--yes]`.
- Reads `NEON_DIRECT_URL` from `os.environ` only, never through `Settings` or `.env`. When it is unset or empty, the script prints that and exits 1.
- Prints `database: <url with hidden password>` and `schema: <current or "empty"> → <head>`.
- When `is_current`, prints `already at <head>, nothing to do` and exits 0 without prompting.
- Otherwise asks the author to type the database name (skipped with `--yes`). A mismatch prints `aborted, nothing was changed` and exits 1.
- On success prints `upgraded to <head>`.
- A `SchemaUpgradeRefused` prints its reason to stderr and exits 1.
- Disposes the engine in `finally`.
- Follows the docstring, argparse, and `_Args` shape of `scripts/reset_database.py`.

#### 2. Runbook

**File**: `README.md`

**Intent**: Record the supported procedure and the ordering responsibility the frame leaves with the author.

**Contract**: a new `## Bringing a Neon database to a commit's schema` section. Its content:

- Check out the commit to deploy.
- Copy Neon's **direct** (non-pooler) connection string.
- Run the script with `NEON_DIRECT_URL` set inline.
- Run it before deploying a commit that adds revisions.
- Never put `NEON_DIRECT_URL` in `backend/.env`, because `Settings` forbids unknown keys.

The section names no particular instance (auth-flow FR-07).

### Success Criteria:

#### Automated Verification:

- `cd backend && uv run basedpyright scripts/migrate_database.py` passes.
- `cd backend && uv run ruff check scripts` passes.
- `cd backend && uv run pytest -m "not postgres"` stays green.

#### Manual Verification:

- Against an empty Neon branch: `cd backend && NEON_DIRECT_URL='<direct url>' uv run python scripts/migrate_database.py`. Type the database name, and expect `upgraded to <head>`. Then `SELECT extname FROM pg_extension WHERE extname = 'vector'` on that branch returns one row.
- Rerun the same command and expect `already at <head>, nothing to do` with no prompt.
- Run with the branch's `-pooler` connection string and expect a refusal naming the direct connection string, exit code 1.
- Run with `NEON_DIRECT_URL` unset and expect the missing-variable message, exit code 1.

---

## Testing Strategy

### Unit Tests:

`backend/tests/unit/adapters/test_schema_upgrade.py`, flat functions:

- `test_direct_asyncpg_url_turns_a_neon_connection_string_into_an_asyncpg_url_with_ssl_and_no_channel_binding`
- `test_direct_asyncpg_url_refuses_a_pooler_host_and_points_at_the_direct_connection_string`
- `test_direct_asyncpg_url_refuses_a_non_postgres_scheme`

### Integration Tests:

`backend/tests/integration/postgres/test_schema_upgrade.py`, `pytestmark = pytest.mark.postgres`, each against a freshly created database from a new fixture in `backend/tests/integration/support/postgres.py`. The fixture reuses the maintenance-connection pattern and drops the database afterwards; it is registered the way `engine` is.

- `test_upgrade_schema_brings_an_empty_database_to_head_with_the_vector_extension`
- `test_upgrade_schema_brings_a_database_one_revision_past_base_to_head`: set up with Alembic's relative `+1` target, so no revision id is hardcoded.
- `test_read_schema_state_refuses_a_database_whose_revision_this_checkout_does_not_know_and_leaves_it_unchanged`: set up with a fabricated `alembic_version` row.

The unmanaged-tables refusal is covered through the same refusal path. If it stays unasserted, record a triage row rather than adding a seventh test to this phase.

### Manual Testing Steps:

See Phase 3 Manual Verification. An empty Neon branch keeps production data out of the check.

## Performance Considerations

On the free tier, Neon suspends compute after 5 minutes idle, and the first connection waits for wake-up, typically under 1 s. asyncpg's default connect timeout of 60 s covers that. No pooling: one engine, one connection, disposed at exit.

## Migration Notes

This change adds no revision. The first run against an empty Neon database applies the whole existing history in one transaction; a failure rolls everything back.

## References

- Frame: `context/efforts/deployment/frame.md` (FR-08; out-of-scope data move and deploy ordering)
- Slice: `context/efforts/deployment/roadmap.md` S-04
- Research: `context/efforts/deployment/research-pg-vector-support.md`, `context/efforts/deployment/research.md` (Neon pooling, SSL, cold start)
- Pattern: `backend/scripts/reset_database.py`, `backend/tests/integration/support/postgres.py`
- Neon agent skills: may help with the manual verification, for example creating an empty branch and reading its direct connection string. Install when needed (not run during planning): `npx neon@latest skills -s neon -s neon-postgres -y`
