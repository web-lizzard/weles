# Remember Persists in Postgres and a Card Rejection Discards the Distill Card Through the Outbox — Implementation Plan

Execution state lives in `todos.md` (sibling of this file), per the `/plan` skill's `references/todos-format.md`.

## Overview

Give remember's three repositories, its two distill-reading ports and its `UnitOfWork` Postgres
implementations, in remember's own Alembic revision. The global in-process lock becomes a
transaction-scoped advisory lock. Prove on real commands that a remember state change commits
together with the envelope it appends, and that on Postgres a card rejection travels through the
outbox and discards the distill card. This is slice S-05 of effort `db-adapter`. It delivers FR-04,
FR-07 and the second half of FR-08 in tests. The daemon keeps running on in-memory adapters until
S-06.

## Current State Analysis

- **Ports.**
  - Domain (`backend/src/domain/remember/ports.py`):
    - `SittingRepository.save/get/latest`;
    - `ReviewEventStore.save/list_by_card/list_by_sitting`, chronological by `reviewed_at`;
    - `SchedulingStateRepository.save/get/get_many`;
    - `ReviewCatalog.list_reviewable/get_reviewable` and `CardSourceLocator.locate`.
  - Application: `UnitOfWork` exposes `sittings`, `review_events`, `scheduling_states` and
    `outbox: OutboxAppender` (`backend/src/application/remember/ports.py:17-28`).
- **Aggregates and records.**
  - `Sitting` (`backend/src/domain/remember/sitting.py`): `id`, `card_ids: frozenset[CardId]`
    (never empty), `opened_at`, `showing_limit` (≥ 1) and `resume_horizon` (a positive `timedelta`).
  - `ReviewEvent` (`backend/src/domain/remember/review_event.py`): `card_id`, `sitting_id`,
    `reviewed_at` and a payload discriminated by `kind`: `Graded(grade)`, `Rejection` or `Reveal`.
    It has no id of its own.
  - `SchedulingState` (`backend/src/domain/remember/scheduling_state.py`): `card_id`, `due_at`,
    `scheduler_state: OpaqueSchedulerState(payload: dict)` and
    `stamp: SchedulerStamp(algorithm, parameter_version)`. `FsrsScheduler` stores the library's
    `Card.to_dict()` as the payload: numbers, nulls and ISO datetime strings.
- **In-memory adapters** (`backend/src/adapters/out/in_memory/remember/`):
  - dict and list stores with snapshot/restore;
  - `InMemoryUnitOfWork`, which acquires an injected module-global `asyncio.Lock` at `__aenter__`
    and releases it at `__aexit__`;
  - `InMemoryReviewCatalog` and `InMemoryCardSourceLocator`, which walk distill's `NoteRepository`
    and `CardRepository` and skip discarded cards.
- **Commands and queries.**
  - `OpenSittingCommand`, `GradeCardCommand`, `RejectCardCommand` and `RevealBackCommand` read the
    catalog and write through the UoW. `RejectCardCommand` appends `card_rejected`.
  - `GradeCardCommand` saves the event and the next state concurrently through `asyncio.TaskGroup`
    (`backend/src/application/remember/commands/grade_card.py:83-85`).
  - `CurrentCardQuery`, `DueCountQuery` and `CardSourceQuery` take the repository ports directly,
    outside any UoW (`backend/src/adapters/compose.py`, `get_current_card_query` and siblings).
- **Worker.** `CardDiscardHandler` consumes `card_rejected` and runs `DiscardCardCommand` with
  `DiscardReason.USER_AUDIT` (`backend/src/adapters/out/worker/handlers/card_discard.py`).
- **Tests.** The five remember contract suites (`backend/tests/unit/remember/contracts/`) use the
  old `_IMPLEMENTATIONS` list with only `in_memory`. The review-event suite saves events for random
  sitting ids. The locator suite has a case that saves a card whose note does not exist.
- **S-02 to S-04 left:**
  - revision `85ec052c2b79` (distill) as head;
  - `Base` with its naming convention, `metadata.py`, and `StrEnumType` in
    `backend/src/adapters/out/sqlalchemy/shared/types.py`;
  - `SqlAlchemyOutboxAppender(session)` and `SqlAlchemyOutboxClaimer(session_factory)`;
  - `SqlAlchemyDistillUnitOfWork` and the distill row models `DistillNoteRow` and `DistillCardRow`;
  - the `engine` and `migrated_database_url` fixtures (`backend/tests/integration/support/postgres.py`);
  - the fixture-param contract pattern with committing wrappers
    (`backend/tests/unit/distill/contracts/test_card_repository_contract.py`);
  - the fresh-engine proof and the relay composition
    (`backend/tests/integration/postgres/test_distill_persistence.py`, `test_distill_relay.py`).

## Desired End State

`backend/src/adapters/out/sqlalchemy/remember/` holds:
- VO column types, row models and `mapping.py`;
- session-bound `SqlAlchemySittingRepository`, `SqlAlchemyReviewEventStore` and
  `SqlAlchemySchedulingStateRepository`;
- `ShortSessionSittingRepository`, `ShortSessionReviewEventStore` and
  `ShortSessionSchedulingStateRepository`, which open one session per call for reads outside a UoW;
- `SqlAlchemyReviewCatalog` and `SqlAlchemyCardSourceLocator`, which read distill's tables;
- `SqlAlchemyRememberUnitOfWork`, holding a transaction-scoped advisory lock.

One Alembic revision creates `remember_sittings`, `remember_sitting_cards`, `remember_review_events`
and `remember_scheduling_states`. The five remember contract suites pass with both `in_memory` and
`postgres` ids. Integration tests on Postgres prove that:
- the three remember queries answer from stored rows through the short-session repositories;
- `GradeCardCommand` commits the review event and the scheduling state together;
- `RejectCardCommand` commits the rejection event and one claimable `card_rejected` envelope
  together, and an exception inside the UoW discards both;
- a second remember UoW enters only after the first one's transaction ends;
- one `OutboxWorker.run_once()` over Postgres turns a rejection into a discarded distill card that
  the SQL catalog no longer offers.

`GradeCardCommand` awaits its two saves in sequence. `compose.py` and `main.py` are unchanged.

Verify: `cd backend && uv run pytest` green, `uv run basedpyright` and `uv run ruff check src tests`
clean, and the Phase 1 manual rows.

### Key Discoveries:
- **`AsyncSession` refuses concurrent operations.** Probed on the dev database: two
  `session.execute` calls in one `TaskGroup` raise `InvalidRequestError: This session is
  provisioning a new connection; concurrent operations are not permitted`. `GradeCardCommand`'s
  `TaskGroup` therefore cannot run on the SQL UoW.
- **`pg_advisory_xact_lock` serializes as the in-memory lock does.** Probed: with a fixed key, a
  second transaction enters only after the first ends. Remember's UoWs never span a model call, so
  the lock is short.
- **`INTERVAL` round-trips `timedelta`.** Probed: `timedelta(hours=26, seconds=3)` reads back as
  `timedelta(days=1, seconds=7203)`, which compares equal.
- **`session.get(Row, VO)` fails** because SQLAlchemy unpacks an iterable Pydantic VO as a composite
  key (S-03, probed). Lookups by primary key go through `select(...).where(...)`.
- **Reads outside a UoW use a short session per call** (effort `frame-log.md`, `reads-outside-uow`).
  The short-session repositories satisfy the full domain ports, so the queries' constructors stay
  unchanged. They also serve as the `postgres` implementation in the contract suites, which replaces
  the test-private `_Committing…` wrappers S-03 and S-04 needed.
- **Adapters may read another module's tables.** Layering constrains `domain/` and `application/`
  only. Remember's SQL catalog and locator import `DistillCardRow` and `DistillNoteRow`, just as
  the in-memory ones import distill's ports.

## What We're NOT Doing

- No change to `adapters/compose.py`, `main.py` or HTTP wiring. The runtime switch is S-06.
- No per-sitting or per-card lock, no optimistic versions, and no conflict error in remember.
- No foreign keys from remember tables to distill tables. `card_id` columns are plain UUIDs.
- No remember-side projection of distill cards. The catalog reads distill's rows directly.
- No change to `OpenSittingCommand`, `RejectCardCommand`, `RevealBackCommand`, the queries, the
  domain or the in-memory adapters. The in-memory UoW keeps its `asyncio.Lock`.
- No BDD scenarios on Postgres. The acceptance suites stay in memory.
- No edit to `context/foundation/testing-conventions.md`.

## Implementation Approach

The work follows the S-03 and S-04 pattern: a stubs phase, then a behaviour phase, for each of three
units.
1. Schema and repositories (Phases 1–2), with the three repository contract suites as the oracle.
2. The distill-reading catalog and locator (Phases 3–4). Their contract suites are the oracle, and
   integration tests show the queries working on the short-session repositories.
3. The unit of work, command atomicity, the lock and the rejection relay (Phases 5–6).

Session ownership follows S-02 to S-04:
- session-bound repositories take the caller's `AsyncSession`, flush after each write and never
  commit;
- `SqlAlchemyRememberUnitOfWork` opens one session per `async with`, takes the advisory lock as its
  first statement, and binds the three repositories and `SqlAlchemyOutboxAppender` to that session;
- short-session repositories, the catalog and the locator take `async_sessionmaker` and open a
  session per call.

## Critical Implementation Details

The advisory lock is transaction-scoped, so `commit` and `rollback` release it. Any statement that
runs after `commit` inside the same `async with` would start an unlocked transaction. No remember
command writes after `commit` today, so do not add a second lock at `__aexit__`.

`remember_review_events.sitting_id` references `remember_sittings.id`, so the review-event contract
suite must save a sitting before its events. The locator case that saves a card with no note cannot
exist on Postgres, because of `distill_cards.note_id`'s foreign key. That case runs `in_memory` only
and skips the `postgres` id, naming the foreign key as the reason.

## Phase 1: Remember schema and Postgres repository stubs

### Overview

Create the remember tables in remember's revision. Materialize the VO column types, row models,
mapping functions and the six repository classes that Phase 2's tests import.

### Changes Required:

#### 1. VO column types

**File**: `backend/src/adapters/out/sqlalchemy/remember/__init__.py`, `backend/src/adapters/out/sqlalchemy/remember/types.py`

**Intent**: Remember row attributes are typed as remember's own value objects.

**Contract**:
- `TypeDecorator` subclasses (`cache_ok = True`):
  - `SittingIdType` and `CardIdType` over `UUID(as_uuid=True)`, for the classes in
    `domain.remember.value_objects`;
  - `ShowingLimitType` over `Integer`;
  - `ResumeHorizonType` over `Interval`;
  - `OpaqueSchedulerStateType` over `JSONB`.
- Bodies raise `NotImplementedError`.

#### 2. Row models and mapping

**File**: `backend/src/adapters/out/sqlalchemy/remember/models.py`, `backend/src/adapters/out/sqlalchemy/remember/mapping.py`, `backend/src/adapters/out/sqlalchemy/metadata.py`

**Intent**: Remember's full state in normalized tables. The database rejects inconsistent events and
invalid limits.

**Contract**:
- `RememberSittingRow`, table `remember_sittings`:
  - `id` PK and `opened_at` TIMESTAMPTZ not null;
  - `showing_limit` INTEGER not null, with CHECK `showing_limit_positive`: `showing_limit >= 1`;
  - `resume_horizon` INTERVAL not null, with CHECK `resume_horizon_positive`:
    `resume_horizon > interval '0'`;
  - index on `opened_at`;
  - relationship `cards` to `RememberSittingCardRow`, with `cascade="all, delete-orphan"`.
- `RememberSittingCardRow`, table `remember_sitting_cards`:
  - `sitting_id` FK → `remember_sittings.id` ON DELETE CASCADE, and `card_id` UUID;
  - PK `(sitting_id, card_id)`.
- `RememberReviewEventRow`, table `remember_review_events`:
  - `id` BIGINT identity PK, which keeps insertion order;
  - `sitting_id` FK → `remember_sittings.id`, not null, and `card_id` UUID not null;
  - `reviewed_at` TIMESTAMPTZ not null;
  - `kind` VARCHAR not null, with a CHECK over `graded`, `rejected` and `revealed`;
  - `grade` VARCHAR null, with a CHECK over `Grade`;
  - CHECK `grade_iff_graded`: `(kind = 'graded') = (grade IS NOT NULL)`;
  - indexes on `(card_id, reviewed_at)` and `(sitting_id, reviewed_at)`.
- `RememberSchedulingStateRow`, table `remember_scheduling_states`:
  - `card_id` PK and `due_at` TIMESTAMPTZ not null;
  - `scheduler_state` JSONB not null;
  - `stamp_algorithm` VARCHAR not null, with a CHECK over `SchedulerAlgorithm`, and
    `stamp_parameter_version` VARCHAR not null.
- `mapping.py` declares `sitting_to_row` / `sitting_to_domain`, `review_event_to_row` /
  `review_event_to_domain` and `scheduling_state_to_row` / `scheduling_state_to_domain`. It
  assembles the payload union and `SchedulerStamp` from their columns. Bodies raise
  `NotImplementedError`.
- `metadata.py` imports the remember models module.

#### 3. Remember revision

**File**: `backend/src/adapters/out/sqlalchemy/migrations/versions/<rev>_create_remember_tables.py`

**Intent**: Remember's own revision (effort boundary: one revision per surface).

**Contract**:
- `down_revision = "85ec052c2b79"`.
- Produced with `alembic -c src/adapters/out/sqlalchemy/alembic.ini revision --autogenerate -m "create remember tables"`,
  then reviewed by hand. VO columns render with their `impl` types, the identity column renders as
  `sa.Identity()`, and the CHECK names follow the `ck_%(table_name)s_%(constraint_name)s` convention.
- `downgrade` drops `remember_review_events`, `remember_sitting_cards`, `remember_scheduling_states`
  and `remember_sittings`, in that order.

#### 4. Repository stubs

**File**: `backend/src/adapters/out/sqlalchemy/remember/sitting_repository.py`, `backend/src/adapters/out/sqlalchemy/remember/review_event_store.py`, `backend/src/adapters/out/sqlalchemy/remember/scheduling_state_repository.py`, `backend/src/adapters/out/sqlalchemy/remember/short_session.py`

**Intent**: The symbols Phase 2's contract tests import. Each port has one repository bound to a
UoW session and one that opens a session per call.

**Contract**:
- `SqlAlchemySittingRepository`, `SqlAlchemyReviewEventStore` and
  `SqlAlchemySchedulingStateRepository`, each with `__init__(self, session: AsyncSession)`.
- `ShortSessionSittingRepository`, `ShortSessionReviewEventStore` and
  `ShortSessionSchedulingStateRepository`, each with
  `__init__(self, session_factory: async_sessionmaker[AsyncSession])`.
- Every class structurally satisfies its domain port. Method bodies raise `NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes
- `cd backend && uv run pytest -m postgres tests/integration/postgres -v` passes

#### Manual Verification:
- `cd backend && uv run alembic -c src/adapters/out/sqlalchemy/alembic.ini upgrade head` exits 0
  on the dev database, and `… current` prints the remember revision as head
- Through the `postgres` MCP server, `select table_name from information_schema.tables where table_name like 'remember_%'`
  lists the four remember tables
- `… downgrade -1` exits 0, and the MCP server no longer finds the remember tables, while the
  distill tables remain; `… upgrade head` restores them

---

## Phase 2: Remember repositories on Postgres

### Overview

Implement the column types, mapping and all six repositories until the sitting, review-event and
scheduling-state contract suites pass on Postgres.

### Changes Required:

#### 1. Column types and mapping

**File**: `backend/src/adapters/out/sqlalchemy/remember/types.py`, `backend/src/adapters/out/sqlalchemy/remember/mapping.py`

**Intent**: Lossless conversion between domain records and rows.

**Contract**:
- Each `TypeDecorator` binds the VO's primitive and rebuilds the VO on read. `None` passes through.
- `Graded(grade)` writes `kind='graded'` with its grade. `Rejection` and `Reveal` write their `kind`
  with a null grade. Reading dispatches on `kind`.
- `card_ids` is written as one card row per id and read back as a `frozenset`.

#### 2. Session-bound repositories

**File**: `backend/src/adapters/out/sqlalchemy/remember/sitting_repository.py`, `backend/src/adapters/out/sqlalchemy/remember/review_event_store.py`, `backend/src/adapters/out/sqlalchemy/remember/scheduling_state_repository.py`

**Intent**: Implement the domain ports inside the caller's transaction, observably identical to the
in-memory adapters.

**Contract**:
- Lookups use `select(Row).where(...)`. Sitting lookups add `selectinload(RememberSittingRow.cards)`.
- `SqlAlchemySittingRepository.save` inserts a missing row. Otherwise it overwrites every column and
  replaces the card rows. `latest` orders by `opened_at DESC` with `LIMIT 1`.
- `SqlAlchemyReviewEventStore.save` always inserts. Both lists order by `reviewed_at, id`.
- `SqlAlchemySchedulingStateRepository.save` inserts a missing row and otherwise overwrites it.
  `get_many` runs one `card_id IN (...)` statement, and returns `{}` without a query for an empty
  input.
- Each write ends with `await session.flush()`, and nothing commits.

#### 3. Short-session repositories

**File**: `backend/src/adapters/out/sqlalchemy/remember/short_session.py`

**Intent**: Reads outside a UoW, one short session per call (effort decision `reads-outside-uow`).

**Contract**:
- Each method opens `async with session_factory() as session` and delegates to the session-bound
  repository.
- `save` commits its own session. It exists to satisfy the port and to seed contract suites, and no
  command uses it.

#### 4. Contract suites over both implementations

**File**: `backend/tests/unit/remember/contracts/test_sitting_repository_contract.py`, `backend/tests/unit/remember/contracts/test_review_event_store_contract.py`, `backend/tests/unit/remember/contracts/test_scheduling_state_repository_contract.py`

**Intent**: One suite per port, run in memory on every invocation and on Postgres under the
`postgres` marker.

**Contract**:
- `_IMPLEMENTATIONS` becomes a sync fixture parametrized over `"in_memory"` and
  `pytest.param("postgres", marks=pytest.mark.postgres)`, as in
  `backend/tests/unit/distill/contracts/test_card_repository_contract.py`.
- The Postgres branch takes `engine` through `request.getfixturevalue` and builds the
  `ShortSession…` repository over `create_session_factory(engine)`.
- The review-event suite's fixture also yields the same implementation's sitting repository, and each
  case saves the sittings its events reference.

#### 5. Schema constraints

**File**: `backend/tests/integration/postgres/test_remember_schema.py`

**Intent**: Pin the integrity guarantees that only Postgres enforces.

**Contract**: module-level `pytestmark = pytest.mark.postgres`. Rows are flushed inside a session,
and the test expects `IntegrityError`.

#### Tests

- the sitting, review-event and scheduling-state contract tests pass with the `postgres` id;
- `latest` returns the sitting with the greatest `opened_at` among three saved out of order;
- two events for one card with equal `reviewed_at` list in the order they were saved;
- a sitting's `card_ids` and `resume_horizon` read back equal after a second save replaces the card
  set;
- a scheduling state produced by `FsrsScheduler.review` reads back equal;
- a `graded` event row with a null grade is rejected by the `grade_iff_graded` CHECK, and an event
  for an unknown sitting is rejected by the foreign key.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/contracts -v` passes with both `in_memory` and
  `postgres` ids
- `cd backend && uv run pytest -m postgres -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Phase 3: Distill-reading catalog and source locator stubs

### Overview

Materialize the two Postgres adapters that turn distill's rows into remember's view, for Phase 4's
contract suites to import.

### Changes Required:

#### 1. Catalog and locator stubs

**File**: `backend/src/adapters/out/sqlalchemy/remember/review_catalog.py`, `backend/src/adapters/out/sqlalchemy/remember/card_source_locator.py`

**Intent**: The one place a distill card row becomes a remember card on Postgres, and the one place
a distill note row becomes a card source.

**Contract**:
- `SqlAlchemyReviewCatalog` and `SqlAlchemyCardSourceLocator`.
- Each has `__init__(self, session_factory: async_sessionmaker[AsyncSession])` and structurally
  satisfies `ReviewCatalog` and `CardSourceLocator` respectively.
- Method bodies raise `NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes

---

## Phase 4: Catalog, source locator and remember queries on Postgres

### Overview

Implement the catalog and the locator in SQL over distill's tables. Show that the three remember
queries answer from Postgres through the short-session repositories.

### Changes Required:

#### 1. Review catalog

**File**: `backend/src/adapters/out/sqlalchemy/remember/review_catalog.py`

**Intent**: Live distill cards as `ReviewableCard`s, read in one statement instead of walking every
note.

**Contract**:
- `list_reviewable` selects `id`, `front` and `back` from `distill_cards` where
  `discard_reason IS NULL`, ordered by `created_at, id`.
- `get_reviewable` adds `id = :card_id` and returns `None` when no live row matches.
- Distill's `CardId` never leaves the adapter. Rows map to remember's `CardId`.

#### 2. Card source locator

**File**: `backend/src/adapters/out/sqlalchemy/remember/card_source_locator.py`

**Intent**: A live card's source blocks and span, read without building distill aggregates.

**Contract**:
- Selects the live card's `anchor_quote` joined to its note's `content`. Returns `None` when there is
  no row.
- Blocks and span come from `NoteDocument.of(content)` and `locate(anchor)`, mapped as in
  `InMemoryCardSourceLocator`. An unlocatable anchor returns `None`.

#### 3. Catalog and locator contract suites

**File**: `backend/tests/unit/remember/contracts/test_review_catalog_contract.py`, `backend/tests/unit/remember/contracts/test_card_source_locator_contract.py`

**Intent**: One suite per port, over both implementations.

**Contract**:
- A fixture parametrized over `"in_memory"` and `pytest.param("postgres", …)` yields the port
  together with distill note and card seeds.
  - In memory, the seeds are the in-memory distill repositories the adapter reads.
  - On Postgres, they are module-private `_Committing…` wrappers over
    `SqlAlchemyNoteRepository` and `SqlAlchemyCardRepository`.
- The existing test functions carry over under their current names.
- `test_locate_returns_none_when_the_note_behind_the_card_is_missing` skips on `postgres`, per
  Critical Implementation Details.

#### 4. Remember queries on Postgres

**File**: `backend/tests/integration/postgres/test_remember_queries.py`

**Intent**: The read side S-06 will wire works end to end on stored rows.

**Contract**:
- Module-level `pytestmark = pytest.mark.postgres`.
- Distill notes and cards are seeded through `SqlAlchemyDistillUnitOfWork`. Sittings, events and
  states are seeded through the `ShortSession…` repositories.
- Each query is built from the `ShortSession…` repositories, `SqlAlchemyReviewCatalog` or
  `SqlAlchemyCardSourceLocator`, `FsrsScheduler`, and a module-private fixed clock.

#### Tests

- every carried-over catalog and locator case passes with the `postgres` id;
- `DueCountQuery` counts a live card with no scheduling state as due, and stops counting it once a
  state due in the future is saved under the current stamp;
- `CurrentCardQuery` presents the stored sitting's only card, with its front, while the sitting is
  offered;
- `CardSourceQuery` returns the card's source blocks and span after a `Reveal` event is stored for
  that card in the sitting;
- the catalog stops offering a card once its distill row is saved with a discard.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/contracts -v` passes with both `in_memory` and
  `postgres` ids
- `cd backend && uv run pytest tests/integration/postgres/test_remember_queries.py -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Phase 5: Remember unit of work stub

### Overview

Materialize the SQL `UnitOfWork` that Phase 6's integration tests import.

### Changes Required:

#### 1. SQL unit of work

**File**: `backend/src/adapters/out/sqlalchemy/remember/unit_of_work.py`

**Intent**: Remember's transaction boundary on Postgres, shared with the outbox appender and
serialized across processes.

**Contract**:
- `class SqlAlchemyRememberUnitOfWork` with
  `__init__(self, session_factory: async_sessionmaker[AsyncSession])`.
- Attributes `sittings: SqlAlchemySittingRepository`, `review_events: SqlAlchemyReviewEventStore`,
  `scheduling_states: SqlAlchemySchedulingStateRepository` and `outbox: SqlAlchemyOutboxAppender`.
- `async def __aenter__(self) -> "SqlAlchemyRememberUnitOfWork"`,
  `async def __aexit__(self, *exc: object) -> None` and `async def commit(self) -> None`.
- A module constant `REMEMBER_LOCK_KEY: int`, a fixed signed 64-bit value.
- Structurally satisfies `application.remember.ports.UnitOfWork`. Bodies raise
  `NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes

---

## Phase 6: Unit of work with advisory lock, atomic commands and the rejection relay on Postgres

### Overview

Implement the SQL `UnitOfWork` and make `GradeCardCommand` safe on one session. Prove FR-04 and
FR-07 through remember's commands, the lock through two concurrent units of work, and the second
half of FR-08 through the real worker and handler on Postgres.

### Changes Required:

#### 1. Unit of work

**File**: `backend/src/adapters/out/sqlalchemy/remember/unit_of_work.py`

**Intent**: The in-memory UoW's semantics, including its serialization, with a real transaction.

**Contract**:
- `__aenter__` opens a session from the factory and executes
  `SELECT pg_advisory_xact_lock(:key)` with `REMEMBER_LOCK_KEY`. It then builds the three
  repositories and `SqlAlchemyOutboxAppender` over that session.
- `commit` commits, which releases the lock.
- `__aexit__` rolls back unless `commit` completed, which also releases the lock, then closes the
  session.
- Each `async with` starts from a fresh session.

#### 2. Sequential saves in GradeCardCommand

**File**: `backend/src/application/remember/commands/grade_card.py`

**Intent**: A unit of work's repositories share one session, which admits one operation at a time.

**Contract**: the `asyncio.TaskGroup` block becomes `await uow.review_events.save(event)` followed by
`await uow.scheduling_states.save(next_state)`, before `await uow.commit()`. The `asyncio` import is
removed. Behaviour on the in-memory adapters is unchanged.

#### 3. Remember persistence integration tests

**File**: `backend/tests/integration/postgres/test_remember_persistence.py`

**Intent**: FR-04 and FR-07 on remember's own commands, and the lock, with no HTTP.

**Contract**:
- Module-level `pytestmark = pytest.mark.postgres`. Tests take `engine` and `migrated_database_url`.
- Commands take `uow_factory=lambda: SqlAlchemyRememberUnitOfWork(create_session_factory(engine))`,
  `SqlAlchemyReviewCatalog`, `FsrsScheduler` and a module-private fixed clock.
- Reviewable cards are seeded through `SqlAlchemyDistillUnitOfWork`.
- A "fresh engine" is a second `create_engine(migrated_database_url)`, read through new
  repositories.
- Envelopes are observed with `SqlAlchemyOutboxClaimer`.

#### 4. Rejection relay integration test

**File**: `backend/tests/integration/postgres/test_remember_relay.py`

**Intent**: A card rejection becomes a discarded distill card, carried only by the outbox on
Postgres (FR-08, second half).

**Contract**:
- A module-private composition builds `OutboxWorker` from `SqlAlchemyOutboxClaimer` and
  `[CardDiscardHandler]` over `DiscardCardCommand` on `SqlAlchemyDistillUnitOfWork`. The batch size,
  attempt limit and worker id match `integration/support/in_memory_remember.py`.
- The test opens a sitting and rejects its card through the SQL remember UoW, runs one
  `run_once()`, and reads the results through a fresh engine.

#### Tests

- after `OpenSittingCommand` and `GradeCardCommand` on Postgres, the graded event and the card's
  scheduling state both read back through a fresh engine;
- `RejectCardCommand` commits the rejection event together with one claimable `card_rejected`
  envelope carrying the card id;
- an exception raised inside the UoW after an event save and an outbox append leaves neither the
  event nor a claimable envelope;
- a second `SqlAlchemyRememberUnitOfWork` enters only after the first one's transaction ends;
- after `RejectCardCommand` and one `run_once()`, the distill card carries a `user_audit` discard
  stamped with the rejection time, `SqlAlchemyReviewCatalog` no longer offers it, and `run_once`
  reports the envelope acked.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration/postgres/test_remember_persistence.py tests/integration/postgres/test_remember_relay.py -v` passes
- `cd backend && uv run pytest tests/unit/remember -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Testing Strategy

### Unit Tests:

- Phase 2 turns the sitting, review-event and scheduling-state contract suites into
  fixture-parametrized suites. The `postgres` id runs over the production short-session
  repositories.
- Phase 4 does the same for the catalog and locator suites, seeding distill rows through committing
  wrappers.
- All suites run in memory by default and on Postgres under the `postgres` marker, so
  `-m 'not postgres'` stays database-free.
- The existing remember command unit tests guard `GradeCardCommand`'s in-memory behaviour across
  the Phase 6 edit.

### Integration Tests:

Four new modules in `tests/integration/postgres/`:
- `test_remember_schema.py` (Phase 2: CHECK and foreign-key rejection);
- `test_remember_queries.py` (Phase 4: the three queries on stored rows);
- `test_remember_persistence.py` (Phase 6: command atomicity, durability and the lock);
- `test_remember_relay.py` (Phase 6: rejection → discarded distill card through the worker).

The `engine` fixture's post-test `TRUNCATE` cleans every remember table. The HTTP and BDD suites
stay in memory.

### Manual Testing Steps:

1. Upgrade the dev database to head through the adapter's `alembic.ini`.
2. Confirm the four remember tables through the `postgres` MCP server.
3. Downgrade one revision, confirm the remember tables are gone and the distill tables remain, then
   upgrade again.

## Performance Considerations

Every remember command and query reads the catalog, which is now one sequential scan of
`distill_cards` filtered on `discard_reason IS NULL`. That is fine for a single user's cards.
`get_many` is one `IN` statement. The advisory lock is held only for a remember command's own
transaction, which never waits on a model. The catalog read inside `GradeCardCommand` uses a second
pooled connection while the UoW holds the first.

## Migration Notes

The remember revision chains onto `85ec052c2b79`. The dev database is at the distill head, so
`upgrade head` applies only this revision. `weles_test` is recreated per test session.

## References

- `context/efforts/db-adapter/frame.md` — FR-04, FR-07, FR-08, one revision per surface, no mixed runtime
- `context/efforts/db-adapter/roadmap.md` — slice S-05
- `context/efforts/db-adapter/frame-log.md` — parked remember concurrency, cross-module reads, reads outside UoW
- `context/efforts/db-adapter/research-sql-alchemy.md` — async session and mapping guidance
- `context/archive/changes/2026-09-13-db-adapter-distill/plan.md` — distill tables, query adapters, relay test
- `context/archive/changes/2026-09-13-db-adapter-capture/plan.md` — TypeDecorator, SQL UoW, fresh-engine proof
- `context/foundation/rules/cqrs-lite.md`, `context/foundation/rules/contract-testing.md`, `context/foundation/rules/layering.md`
- `context/foundation/testing-conventions.md` — test layout, naming, doubles
