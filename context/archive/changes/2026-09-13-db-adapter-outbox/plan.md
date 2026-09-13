# Outbox Envelopes Persist in Postgres — Implementation Plan

Execution state lives in `todos.md` (sibling of this file), per the `/plan` skill's `references/todos-format.md`.

## Overview

Give the shared outbox a Postgres implementation. The `outbox_envelopes` table arrives in the
first real Alembic revision. Postgres adapters implement `OutboxAppender`, `OutboxClaimer` and
`OutboxEnvelopeQueryPort`. The existing outbox contract suite runs against both the in-memory
and the Postgres implementations, and a few integration tests prove that an envelope's full
state survives a fresh engine and that `OutboxWorker` runs on the Postgres claimer. This is slice
S-02 of effort `db-adapter` and delivers FR-01 in tests; the daemon keeps running on in-memory
adapters until S-06.

## Current State Analysis

- The domain envelope is `OutboxEnvelope` (`backend/src/domain/shared/outbox/model.py:38-84`):
  `EnvelopeId`, `EnvelopeType(name, version)`, `payload: dict[str, object]`, `EnvelopeStatus`,
  `attempts`, `created_at`, `claimed_at`, `claimed_by`. Its `claim` / `consume` / `fail`
  methods own every state transition.
- Ports: `OutboxAppender.append` and `OutboxClaimer.claim/ack/fail`
  (`backend/src/domain/shared/outbox/ports.py`); `OutboxEnvelopeQueryPort.list_envelopes`
  (`backend/src/application/shared/outbox/queries/envelopes.py`) returns `OutboxEnvelopeDTO`.
- In-memory adapters share one `InMemoryOutboxStore`
  (`backend/src/adapters/out/in_memory/shared/outbox/`). The claimer serialises claims with an
  `asyncio.Lock`, selects pending envelopes of an exact `EnvelopeType` ordered by `created_at`,
  and calls the domain `claim` on each. `ack` and `fail` just re-put the mutated envelope.
- Capture, distill and remember UoWs all receive the same appender and roll it back through
  store snapshots (`backend/src/adapters/out/in_memory/*/unit_of_work.py`), wired in
  `backend/src/adapters/compose.py:119-122`.
- The outbox contract suite (`backend/tests/unit/shared/test_outbox_contract.py`) has five tests
  parametrized over `_IMPLEMENTATIONS: list[Callable[[], tuple[OutboxAppender, OutboxClaimer]]]`
  with only `in_memory`. It includes a concurrent-claims-are-disjoint test.
- S-01 left `backend/src/adapters/out/sqlalchemy/` with `create_engine`,
  `create_session_factory`, `upgrade_to_head`, a dual-path `env.py` with `target_metadata = None`,
  and an empty `versions/`. The Postgres fixtures `migrated_database_url` and `engine` live in
  `backend/tests/integration/postgres/conftest.py`, visible only under that directory.
- `test_database_tooling.py:21-32` asserts a freshly migrated database has **no** applied
  revision — true only while the history is empty.

## Desired End State

`backend/src/adapters/out/sqlalchemy/shared/outbox/` holds a row model, mapping, and Postgres
appender, claimer and envelope query adapter. One Alembic revision creates `outbox_envelopes`
and drops it on downgrade. `uv run pytest tests/unit/shared/test_outbox_contract.py -v` runs
every contract test with both the `in_memory` and `postgres` ids and passes. The Postgres suite
also proves:

- an appended envelope commits or rolls back with the session it was appended in;
- an envelope's full state reads back through a fresh engine;
- the query adapter lists envelopes with their current status;
- `OutboxWorker` retries and dead-letters on the Postgres claimer.

`compose.py` and `main.py` are unchanged.

Verify: `cd backend && uv run pytest` green, `uv run basedpyright` and
`uv run ruff check src tests` clean, and the Phase 1 manual rows.

### Key Discoveries:
- `postgres-mcp`, `TEST_DATABASE_URL` and the `postgres` marker already exist from S-01
  (`backend/pyproject.toml` markers; `.devcontainer/docker-compose.yml`).
- A sync fixture parametrized with `pytest.param("postgres", marks=pytest.mark.postgres)` can
  pull the async function-scoped `engine` fixture through `request.getfixturevalue("engine")`
  under pytest 9.1.1 / pytest-asyncio 1.4.0 — probed. `-m 'not postgres'` then deselects only the
  Postgres ids.
- `SELECT … FOR UPDATE SKIP LOCKED` in two concurrent sessions hands out disjoint rows on the
  compose Postgres — probed with two `asyncio.gather`ed claims.
- `pytest_plugins` is accepted in `backend/tests/conftest.py` because it is loaded before
  configuration completes; pytest rejects it only in conftests loaded later
  (`_pytest/config/__init__.py` `_check_non_top_pytest_plugins`).
- Reads outside a UoW use a short session per call (effort `frame-log.md`, decision
  `reads-outside-uow`), which fixes how the claimer and query adapter obtain sessions.

## What We're NOT Doing

- No change to `adapters/compose.py` or `main.py`; the daemon stays in memory until S-06.
- No SQLAlchemy `UnitOfWork` for any module; capture's is S-03. The appender is only shaped to be
  used inside one.
- No cross-module relay tests (S-04, S-05).
- No change to the domain model, the ports, `OutboxWorker`, or the in-memory adapters.
- No stale-claim recovery for envelopes left `processing` by a crashed worker — the in-memory
  adapter has none either.
- No edit to `context/foundation/testing-conventions.md`; the new shared Postgres fixture plugin
  is recorded there by `/testing-shape`.

## Implementation Approach

Schema and stubs first, then append and claim behaviour, then the query adapter and the
integration proof. The contract suite becomes the Postgres adapters' oracle unchanged, because
the slice requires append, claim, ack and fail to behave identically.

The domain stays the only owner of envelope state transitions. The claimer locks candidate rows
with `SKIP LOCKED`, maps them to `OutboxEnvelope`, calls `envelope.claim(worker_id)`, and writes
the resulting state back in the same transaction. `ack` and `fail` persist whatever state the
caller's domain call produced. No status arithmetic is duplicated in SQL.

Session ownership follows the ports' future callers. The appender takes the caller's
`AsyncSession` and never commits, so S-03's UoW makes the envelope atomic with module state. The
claimer and query adapter take an `async_sessionmaker` and open one short transaction per call.

## Critical Implementation Details

Adding the first revision breaks
`test_upgrading_fresh_database_leaves_alembic_version_with_no_applied_revision`, which asserts an
empty `alembic_version`. Phase 1 rewrites it to assert the table holds exactly the script
directory's head revision; otherwise the phase cannot close green.

The claim's row locks are what make concurrent claims disjoint, so the `SELECT … FOR UPDATE SKIP
LOCKED`, the domain `claim` calls and the write-back must share one transaction that commits only
after every claimed row is updated. Order comes from the `SELECT`'s `ORDER BY created_at`; do not
rely on `UPDATE … RETURNING` order.

## Phase 1: Outbox schema and Postgres appender/claimer stubs

### Overview

Create the outbox table through the first Alembic revision, materialize the Postgres appender and
claimer symbols, and make the Postgres fixtures visible to the whole test tree.

### Changes Required:

#### 1. Declarative base and migration metadata

**File**: `backend/src/adapters/out/sqlalchemy/base.py`, `backend/src/adapters/out/sqlalchemy/metadata.py`

**Intent**: One metadata object every surface's models register on, with deterministic constraint
names so revisions stay reviewable, and one import point Alembic reads it from.

**Contract**: `class Base(DeclarativeBase)` whose `metadata` carries a naming convention for
`ix`, `uq`, `ck`, `fk`, `pk`. `metadata.py` imports each model module (only the outbox one in
this change) and exposes `target_metadata = Base.metadata`.

#### 2. Outbox row model and mapping

**File**: `backend/src/adapters/out/sqlalchemy/shared/__init__.py`, `backend/src/adapters/out/sqlalchemy/shared/outbox/__init__.py`, `backend/src/adapters/out/sqlalchemy/shared/outbox/models.py`, `backend/src/adapters/out/sqlalchemy/shared/outbox/mapping.py`

**Intent**: Store an envelope's full state in one row, mirroring the in-memory package layout.

**Contract**: `OutboxEnvelopeRow` on table `outbox_envelopes`:
- `id` UUID primary key;
- `type_name` VARCHAR not null, `type_version` INTEGER not null;
- `payload` JSONB not null;
- `status` VARCHAR not null, with a CHECK over the four `EnvelopeStatus` values;
- `attempts` INTEGER not null;
- `created_at` TIMESTAMPTZ not null, `claimed_at` TIMESTAMPTZ null;
- `claimed_by` VARCHAR null.

Partial index on `(type_name, type_version, created_at)` `WHERE status = 'pending'`.
`mapping.py`: `def to_row(envelope: OutboxEnvelope) -> OutboxEnvelopeRow` and
`def to_envelope(row: OutboxEnvelopeRow) -> OutboxEnvelope`. Bodies raise `NotImplementedError`.

#### 3. Alembic environment metadata and first revision

**File**: `backend/src/adapters/out/sqlalchemy/migrations/env.py`, `backend/src/adapters/out/sqlalchemy/migrations/versions/<rev>_create_outbox_envelopes.py`

**Intent**: The outbox surface's own revision (effort boundary: one revision per surface), and
autogenerate that sees the models.

**Contract**: `env.py` sets `target_metadata` from `adapters.out.sqlalchemy.metadata`; both entry
paths otherwise unchanged. The revision is produced with
`alembic -c src/adapters/out/sqlalchemy/alembic.ini revision --autogenerate -m "create outbox envelopes"`
against a database at head, then reviewed. `upgrade` creates the table, CHECK and partial index;
`downgrade` drops them. `down_revision = None`.

#### 4. Postgres appender and claimer stubs

**File**: `backend/src/adapters/out/sqlalchemy/shared/outbox/appender.py`, `backend/src/adapters/out/sqlalchemy/shared/outbox/claimer.py`

**Intent**: Symbols the Phase 2 tests import.

**Contract**:
- `class SqlAlchemyOutboxAppender` with `__init__(self, session: AsyncSession)` and
  `async def append(self, envelope: OutboxEnvelope) -> None`.
- `class SqlAlchemyOutboxClaimer` with
  `__init__(self, session_factory: async_sessionmaker[AsyncSession])`,
  `async def claim(self, envelope_type: EnvelopeType, limit: int, worker_id: str) -> list[OutboxEnvelope]`,
  `async def ack(self, envelope: OutboxEnvelope) -> None` and
  `async def fail(self, envelope: OutboxEnvelope) -> None`.

Both structurally satisfy the domain ports. Method bodies raise `NotImplementedError`.

#### 5. Shared Postgres fixtures

**File**: `backend/tests/integration/support/postgres.py`, `backend/tests/conftest.py`, `backend/tests/integration/postgres/conftest.py` (deleted)

**Intent**: Let the outbox contract suite under `tests/unit/` request the database fixtures that
today only `tests/integration/postgres/` can see.

**Contract**: `migrated_database_url` and `engine` move verbatim into
`integration.support.postgres`. `tests/conftest.py` gains
`pytest_plugins = ["integration.support.postgres"]`. Fixture names, scopes and failure messages
are unchanged.

#### 6. Tooling test for a non-empty history

**File**: `backend/tests/integration/postgres/test_database_tooling.py`

**Intent**: Keep S-01's tooling proof true now that a revision exists.

**Contract**: the fresh-upgrade test is renamed
`test_upgrading_fresh_database_stamps_alembic_version_at_head` and asserts `alembic_version`
holds exactly the head of `ScriptDirectory.from_config(alembic_config())`. The other three tests
are unchanged.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes
- `cd backend && uv run pytest -m postgres tests/integration/postgres -v` passes

#### Manual Verification:
- `cd backend && uv run alembic -c src/adapters/out/sqlalchemy/alembic.ini upgrade head` exits 0
  on the dev database, and `… current` prints the new revision as head
- Through the `postgres` MCP server, `select column_name, data_type, is_nullable from
  information_schema.columns where table_name = 'outbox_envelopes'` lists the eight columns
- `… downgrade -1` exits 0 and the MCP server no longer finds `outbox_envelopes`; `… upgrade head`
  restores it

---

## Phase 2: Postgres append and claim

### Overview

Implement the appender and claimer until the outbox contract suite passes on Postgres, and prove
an append is bound to its session's transaction.

### Changes Required:

#### 1. Mapping

**File**: `backend/src/adapters/out/sqlalchemy/shared/outbox/mapping.py`

**Intent**: Lossless conversion between envelope and row.

**Contract**: as Phase 1. `EnvelopeType` splits into `type_name` / `type_version`; `status` is
stored as the enum's value; `payload` round-trips as JSON.

#### 2. Appender

**File**: `backend/src/adapters/out/sqlalchemy/shared/outbox/appender.py`

**Intent**: Stage the envelope in the caller's transaction, so it commits or rolls back with
whatever else that session writes.

**Contract**: `append` adds `to_row(envelope)` to the injected session. It never commits.

#### 3. Claimer

**File**: `backend/src/adapters/out/sqlalchemy/shared/outbox/claimer.py`

**Intent**: Hand each pending envelope to exactly one concurrent claimer, with the domain deciding
the claimed state.

**Contract**: `claim` opens one session and transaction. It selects up to `limit` rows with
`status = 'pending'` and the exact `type_name` and `type_version`, ordered by `created_at`,
`FOR UPDATE SKIP LOCKED`. It maps them to envelopes, calls `claim(worker_id)` on each, writes
`status`, `attempts`, `claimed_at` and `claimed_by` back by id, commits, and returns the
envelopes in select order. `ack` and `fail` each open a session and transaction that write the
same four fields from the given envelope by id, then commit.

#### 4. Contract suite over both implementations

**File**: `backend/tests/unit/shared/test_outbox_contract.py`

**Intent**: One suite for the outbox ports, run against in-memory on every invocation and against
Postgres under the `postgres` marker.

**Contract**: `_IMPLEMENTATIONS` is replaced by a sync fixture yielding
`tuple[OutboxAppender, OutboxClaimer]`. It is parametrized over `"in_memory"` and
`pytest.param("postgres", marks=pytest.mark.postgres)`; the Postgres branch gets `engine` through
`request.getfixturevalue`. Because the contract has no transaction concept, the Postgres appender
is wrapped by a module-private `_CommittingAppender` that opens a session, appends through
`SqlAlchemyOutboxAppender` and commits. The five existing test bodies stay unchanged apart from
taking the fixture.

#### 5. Append atomicity tests

**File**: `backend/tests/integration/postgres/test_outbox_append_atomicity.py`

**Intent**: Show the appender joins the session's transaction — the ground S-03's FR-07 stands on.

**Contract**: module-level `pytestmark = pytest.mark.postgres`; tests take `engine`, and they
observe results through `SqlAlchemyOutboxClaimer`.

#### Tests

- the contract suite's five tests pass with the `postgres` id, including disjoint concurrent claims;
- an envelope appended in a session that rolls back is never claimable;
- an envelope appended in a session that commits is claimable from another session.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/shared/test_outbox_contract.py -v` passes with both
  `in_memory` and `postgres` ids
- `cd backend && uv run pytest -m postgres -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Phase 3: Postgres envelope query stubs

### Overview

Materialize the Postgres query adapter the Phase 4 tests import.

### Changes Required:

#### 1. Envelope query adapter stub

**File**: `backend/src/adapters/out/sqlalchemy/shared/outbox/envelope_query.py`

**Intent**: The Postgres side of `GET /_outbox`, ready for the runtime switch.

**Contract**: `class SqlAlchemyOutboxEnvelopeQueryAdapter` with
`__init__(self, session_factory: async_sessionmaker[AsyncSession])` and
`async def list_envelopes(self) -> list[OutboxEnvelopeDTO]`, structurally satisfying
`OutboxEnvelopeQueryPort`. Body raises `NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes

---

## Phase 4: Envelope state survives a fresh engine and the worker runs on Postgres

### Overview

Implement the query adapter, and prove FR-01's full state and the worker loop on a real Postgres.

### Changes Required:

#### 1. Envelope query adapter

**File**: `backend/src/adapters/out/sqlalchemy/shared/outbox/envelope_query.py`

**Intent**: List envelopes straight into DTO shape, as CQRS-lite queries do.

**Contract**: one short session per call. Every row is read ordered by `created_at` and built
directly into `OutboxEnvelopeDTO`, with no `OutboxEnvelope` reconstruction. `type` is
`str(EnvelopeType(name=type_name, version=type_version))` (`note_approved@1`) and `status` is the
stored value.

#### 2. Outbox persistence integration tests

**File**: `backend/tests/integration/postgres/test_outbox_persistence.py`

**Intent**: FR-01 in tests — nothing about an envelope lives only in the process that wrote it —
and the worker's retry/dead-letter loop on the Postgres claimer.

**Contract**: module-level `pytestmark = pytest.mark.postgres`; tests take `engine` and
`migrated_database_url`. A "fresh engine" is a second `create_engine(migrated_database_url)` built
after the writing engine is disposed. `OutboxWorker` is composed in the test with a module-private
failing handler.

#### Tests

- an envelope appended, claimed and failed for retry on one engine is claimed again through a
  fresh engine with its nested payload, type version, `created_at` and an incremented attempt
  count intact;
- an envelope claimed on one engine is listed through a fresh engine's query adapter as
  `processing` with its worker id and claim time;
- the query adapter lists each envelope with its `name@version` type and current status;
- `OutboxWorker` on the Postgres claimer returns an envelope to pending after a handler failure
  and dead-letters it as `failed` once `max_attempts` is reached.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration/postgres/test_outbox_persistence.py -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Testing Strategy

### Unit Tests:

The outbox contract suite in `tests/unit/shared/` is the only unit-level change: the same five
behaviours, now also run against Postgres under the `postgres` marker. `-m 'not postgres'` keeps
the unit run database-free.

### Integration Tests:

Two new modules in `tests/integration/postgres/`: append atomicity (two tests) and outbox
persistence (four tests). They run on real commits with the `engine` fixture's post-test
`TRUNCATE`, so commit and rollback semantics are genuine.

### Manual Testing Steps:

1. Upgrade the dev database to head through the adapter's `alembic.ini`.
2. Inspect `outbox_envelopes` through the `postgres` MCP server.
3. Downgrade one revision, confirm the table is gone, and upgrade again.

## Performance Considerations

Claiming uses a partial index on pending rows by type and age, so claim cost tracks the pending
backlog rather than total history. Consumed and failed rows are never pruned in this change.

## Migration Notes

The first revision has `down_revision = None`. The dev database already carries an
`alembic_version` table from S-01's manual step, so `upgrade head` applies only this revision.
`weles_test` is recreated per test session and needs nothing.

## References

- `context/efforts/db-adapter/frame.md` — FR-01, one revision per surface, no mixed runtime
- `context/efforts/db-adapter/roadmap.md` — slice S-02
- `context/efforts/db-adapter/frame-log.md` — parked worker claiming, reads outside UoW
- `context/efforts/db-adapter/research-sql-alchemy.md` — async session and mapping guidance
- `context/archive/changes/2026-09-13-db-adapter-setup/plan.md` — engine, Alembic bridge, fixtures
- `context/foundation/rules/contract-testing.md` — one suite per port over its implementations
- `context/foundation/rules/cqrs-lite.md` — queries read straight into DTOs
- `context/foundation/testing-conventions.md` — test layout, naming, doubles
- <https://www.postgresql.org/docs/16/sql-select.html#SQL-FOR-UPDATE-SHARE> — `SKIP LOCKED`
