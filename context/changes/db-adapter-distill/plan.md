# Distill Persists in Postgres and a Capture Approval Becomes Cards Through the Outbox — Implementation Plan

Execution state lives in `todos.md` (sibling of this file), per the `/plan` skill's `references/todos-format.md`.

## Overview

Give distill's two repositories, its three query ports and its `UnitOfWork` Postgres
implementations, in distill's own Alembic revision. Prove on real commands that a distill state
change commits together with the envelope it appends. Then prove that on Postgres a capture note
approval travels through the outbox, becomes a distill note, and then becomes that note's cards.
This is slice S-04 of effort `db-adapter`. It delivers FR-03, FR-07 and the first half of FR-08 in
tests. The daemon keeps running on in-memory adapters until S-06.

## Current State Analysis

- **Ports.**
  - Domain: `NoteRepository.save/get/list_all` and `CardRepository.save/get/list_by_note`
    (`backend/src/domain/distill/ports.py:11-24`).
  - Application: `UnitOfWork` exposes `notes`, `cards` and `outbox: OutboxAppender`
    (`backend/src/application/distill/ports.py:7-16`).
  - Query ports: `ListNotesQueryPort`, `GetNoteQueryPort` and `ListCardsForNoteQueryPort`
    (`backend/src/application/distill/queries/`).
- **Aggregates.**
  - `Note` (`backend/src/domain/distill/note.py:16-25`) carries:
    - an embedded `TopicSnapshot(id, label)` and an ordered `list[TagSnapshot]`;
    - `DistillationStatus`;
    - `approved_at`, `created_at` and `updated_at`.
  - `Card` (`backend/src/domain/distill/card.py:15-22`) carries:
    - `note_id`;
    - `front` and `back` (`CardSide`) and `anchor` (`Anchor.quote`);
    - `discard: Discard | None`, where `Discard` is `reason`, `detail` and `discarded_at`;
    - `created_at`.
- **In-memory adapters** (`backend/src/adapters/out/in_memory/distill/`):
  - dict repositories and a snapshot-restore `InMemoryUnitOfWork`;
  - three query adapters that compose the repositories:
    - `list_notes` counts live cards and orders by `max(note.updated_at, live card created_at)`,
      descending;
    - `get_note` builds blocks with `NoteDocument`;
    - `list_cards_for_note` returns live cards sorted by `created_at`, each with an anchor location.
- **Tests.**
  - The note and card contract suites (`backend/tests/unit/distill/contracts/`) use the old
    `_IMPLEMENTATIONS` list with only `in_memory`. The card suite saves cards for random
    `NoteId`s that have no note.
  - The query adapters are tested only in memory (`test_list_notes_query.py`,
    `test_get_note_query.py`). `list_cards_for_note` has only HTTP coverage
    (`backend/tests/integration/test_notes_http.py:121-208`).
- **Commands.**
  - `SaveNoteCommand` mints and saves a note, then appends `note_saved` before one commit. It
    treats an existing note as a redelivery.
  - `GenerateCardsCommand` keeps its UoW open for the whole model run. It saves new cards and
    marks the note ready or failed.
  - `DiscardCardCommand` sets `card.discard` and saves the card.
- **Worker.**
  - `SaveNoteHandler` consumes `note_approved` and `FlashcardGenHandler` consumes `note_saved`
    (`backend/src/adapters/out/worker/handlers/`).
  - `OutboxWorker.run_once` walks its handlers in order, so an envelope appended by the first
    handler is claimable by the second in the same pass
    (`backend/src/adapters/out/worker/outbox_worker.py:26-43`).
- **S-02 and S-03 left:**
  - `Base` with a naming convention, and `metadata.py`;
  - revision `2ce37af2f0f8` (capture) as head;
  - `SqlAlchemyOutboxAppender(session)` and `SqlAlchemyOutboxClaimer(session_factory)`, which
    uses `SKIP LOCKED`;
  - `SqlAlchemyCaptureUnitOfWork`;
  - VO `TypeDecorator`s, including the generic `StrEnumType`, in
    `backend/src/adapters/out/sqlalchemy/capture/types.py`;
  - the `engine` and `migrated_database_url` fixtures (`backend/tests/integration/support/postgres.py`);
  - the fixture-param contract pattern with module-private `_Committing…` wrappers and a seed for
    parent rows (`backend/tests/unit/capture/contracts/test_note_repository_contract.py`).

## Desired End State

`backend/src/adapters/out/sqlalchemy/distill/` holds:
- VO column types, row models and `mapping.py`;
- `SqlAlchemyNoteRepository` and `SqlAlchemyCardRepository`;
- `SqlAlchemyListNotesQueryAdapter`, `SqlAlchemyGetNoteQueryAdapter` and
  `SqlAlchemyListCardsForNoteQueryAdapter`;
- `SqlAlchemyDistillUnitOfWork`.

`StrEnumType` lives in `backend/src/adapters/out/sqlalchemy/shared/types.py`, and capture imports it
from there.

One Alembic revision creates `distill_notes`, `distill_note_tags` and `distill_cards`. The note
contract suite, the card contract suite and three query contract suites pass with both `in_memory`
and `postgres` ids. Integration tests on Postgres prove that:
- `SaveNoteCommand` commits the note and one claimable `note_saved` envelope together;
- an exception inside the UoW discards the note and the envelope together;
- a discard written by `DiscardCardCommand` survives a fresh engine;
- one `OutboxWorker.run_once()` over Postgres turns an approved capture note into a ready distill
  note with its cards, and consumes both envelopes.

`compose.py` and `main.py` are unchanged.

Verify: `cd backend && uv run pytest` green, `uv run basedpyright` and `uv run ruff check src tests`
clean, and the Phase 1 manual rows.

### Key Discoveries:
- **Snapshots carry no foreign keys to capture.** Distill never reads capture's stores (roadmap
  S-04), so `distill_notes.session_id`, `topic_id` and `distill_note_tags.tag_id` are plain UUIDs.
- **Multi-column VOs are assembled in `mapping.py`.** `TopicSnapshot` spans two columns and
  `Discard` spans three. As S-03 probed, `composite()` cannot build the Pydantic VOs, so mapping
  assembles them, the same way capture assembles `Embedding`.
- **`session.get(Row, VO)` fails** because SQLAlchemy unpacks an iterable Pydantic VO as a composite
  key (S-03, probed). Lookups by primary key go through `select(...).where(...)`.
- **Queries read into DTOs, not aggregates** (`context/foundation/rules/cqrs-lite.md`). Only
  `NoteDocument.of(NoteContent(...))` stays in Python, for blocks and anchor locations.
- **Reads outside a UoW use a short session per call** (effort `frame-log.md`, `reads-outside-uow`).
  The query adapters take `async_sessionmaker` and open one session per method call.
- **The in-memory relay composition** (`backend/tests/integration/support/in_memory_distill.py`)
  already fixes the worker shape: handlers in the order `[SaveNoteHandler, FlashcardGenHandler]`,
  `DeterministicStructuredTaskAdapter`, a `CardFactory` with 200/600 limits, and a never-regenerate
  policy. The deterministic adapter always proposes one fabricated control card, which ends up
  discarded as `ungrounded`.

## What We're NOT Doing

- No change to `adapters/compose.py`, `main.py` or HTTP wiring. The query adapters and the UoW are
  composed only in tests, and the runtime switch is S-06.
- No remember tables, and no `card_rejected` → discard relay on Postgres (S-05).
- No optimistic versions, row locks or advisory locks on distill tables.
- No foreign keys from distill tables to capture tables.
- No BDD scenarios on Postgres. The acceptance suites stay in memory.
- No edit to `context/foundation/testing-conventions.md`.

## Implementation Approach

The work follows S-03's pattern: a stubs phase, then a behaviour phase, for each of three units.
1. Schema and repositories (Phases 1–2), with the existing note and card contract suites as the
   oracle.
2. Query adapters (Phases 3–4), where today's in-memory query tests become contract suites for
   both implementations.
3. The unit of work, command atomicity and the cross-module relay (Phases 5–6).

Session ownership follows S-02 and S-03:
- repositories take the caller's `AsyncSession`, flush after each write and never commit;
- `SqlAlchemyDistillUnitOfWork` opens one session per `async with` and binds both repositories and
  `SqlAlchemyOutboxAppender` to it;
- query adapters own a short session per call.

Concurrency has no adapter mechanism. The claimer's `SKIP LOCKED` hands an envelope to one handler,
and every distill command is idempotent on redelivery. `GenerateCardsCommand` saves only cards it
minted, and `DiscardCardCommand` touches only an existing card.

## Critical Implementation Details

A concurrent redelivery of `note_approved` can make two `SaveNoteCommand`s both see no note. The
second insert then fails on the primary key, and the worker marks that envelope failed. Its retry
finds the note and becomes a no-op. This is the accepted outcome, so do not catch `IntegrityError`
in the repository.

`distill_cards` has a foreign key to `distill_notes`. `GenerateCardsCommand` reads the note before
saving its cards, so insert order already holds. Contract and query suites must seed the note first.

## Phase 1: Distill schema and Postgres repository stubs

### Overview

Create the distill tables in distill's revision. Materialize the VO column types, row models,
mapping functions and the two repository classes that Phase 2's tests import.

### Changes Required:

#### 1. Shared enum column type

**File**: `backend/src/adapters/out/sqlalchemy/shared/types.py`, `backend/src/adapters/out/sqlalchemy/capture/types.py`, `backend/src/adapters/out/sqlalchemy/capture/models.py`

**Intent**: Distill needs `StrEnumType` without importing capture's adapter package.

**Contract**:
- `StrEnumType[EnumT: StrEnum]` moves unchanged to `sqlalchemy/shared/types.py`.
- `capture/types.py` no longer defines it, and `capture/models.py` imports it from the shared
  module.
- Revision `2ce37af2f0f8` is untouched, because it renders enum columns as `sa.String()`.

#### 2. VO column types

**File**: `backend/src/adapters/out/sqlalchemy/distill/__init__.py`, `backend/src/adapters/out/sqlalchemy/distill/types.py`

**Intent**: Distill row attributes are typed as distill's own value objects.

**Contract**:
- `TypeDecorator` subclasses (`cache_ok = True`):
  - `NoteIdType`, `SessionIdType` and `CardIdType` over `UUID(as_uuid=True)`, for the classes in
    `domain.distill.value_objects`;
  - `NoteContentType`, `CardSideType` and `AnchorType` (`Anchor.quote`) over `Text`.
- Bodies raise `NotImplementedError`.

#### 3. Row models and mapping

**File**: `backend/src/adapters/out/sqlalchemy/distill/models.py`, `backend/src/adapters/out/sqlalchemy/distill/mapping.py`, `backend/src/adapters/out/sqlalchemy/metadata.py`

**Intent**: Distill's full state in normalized tables. The database rejects orphan cards and
half-written discards.

**Contract**:
- `DistillNoteRow`, table `distill_notes`:
  - `id` PK; `session_id` UUID not null, with no FK;
  - `topic_id` UUID and `topic_label` VARCHAR, both not null;
  - `content` TEXT;
  - `distillation_status` with a CHECK over `DistillationStatus`;
  - `approved_at`, `created_at` and `updated_at` TIMESTAMPTZ not null;
  - relationship `tags` to `DistillNoteTagRow`, ordered by `position`, with
    `cascade="all, delete-orphan"`.
- `DistillNoteTagRow`, table `distill_note_tags`:
  - `note_id` FK → `distill_notes.id` ON DELETE CASCADE;
  - `position` INTEGER, `tag_id` UUID and `label` VARCHAR;
  - PK `(note_id, position)`.
- `DistillCardRow`, table `distill_cards`:
  - `id` PK; `note_id` FK → `distill_notes.id`, not null;
  - `front`, `back` and `anchor_quote` TEXT not null;
  - `discard_reason` VARCHAR null, with a CHECK over `DiscardReason`;
  - `discard_detail` TEXT null and `discarded_at` TIMESTAMPTZ null;
  - `created_at` TIMESTAMPTZ not null;
  - CHECK `discard_complete`: `(discard_reason IS NULL) = (discarded_at IS NULL)`;
  - CHECK `discard_detail_needs_reason`: `discard_reason IS NOT NULL OR discard_detail IS NULL`;
  - index on `(note_id, created_at)`.
- `mapping.py` declares `note_to_row` / `note_to_domain` and `card_to_row` / `card_to_domain`. It
  assembles `TopicSnapshot`, `TagSnapshot` and `Discard` from their columns. Bodies raise
  `NotImplementedError`.
- `metadata.py` imports the distill models module.

#### 4. Distill revision

**File**: `backend/src/adapters/out/sqlalchemy/migrations/versions/<rev>_create_distill_tables.py`

**Intent**: Distill's own revision (effort boundary: one revision per surface).

**Contract**:
- `down_revision = "2ce37af2f0f8"`.
- Produced with `alembic -c src/adapters/out/sqlalchemy/alembic.ini revision --autogenerate -m "create distill tables"`,
  then reviewed by hand. VO columns render with their `impl` types, and the CHECK names follow the
  `ck_%(table_name)s_%(constraint_name)s` convention.
- `downgrade` drops `distill_cards`, `distill_note_tags` and `distill_notes`, in that order.

#### 5. Repository stubs

**File**: `backend/src/adapters/out/sqlalchemy/distill/note_repository.py`, `backend/src/adapters/out/sqlalchemy/distill/card_repository.py`

**Intent**: Symbols the Phase 2 contract tests import.

**Contract**:
- `SqlAlchemyNoteRepository` and `SqlAlchemyCardRepository`.
- Each has `__init__(self, session: AsyncSession)` and structurally satisfies its domain port.
- Method bodies raise `NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes
- `cd backend && uv run pytest -m postgres tests/integration/postgres -v` passes

#### Manual Verification:
- `cd backend && uv run alembic -c src/adapters/out/sqlalchemy/alembic.ini upgrade head` exits 0
  on the dev database, and `… current` prints the distill revision as head
- Through the `postgres` MCP server, `select table_name from information_schema.tables where table_name like 'distill_%'`
  lists the three distill tables
- `… downgrade -1` exits 0, and the MCP server no longer finds the distill tables, while the
  capture tables remain; `… upgrade head` restores them

---

## Phase 2: Distill repositories on Postgres

### Overview

Implement the column types, mapping and both repositories until the note and card contract suites
pass on Postgres.

### Changes Required:

#### 1. Column types and mapping

**File**: `backend/src/adapters/out/sqlalchemy/distill/types.py`, `backend/src/adapters/out/sqlalchemy/distill/mapping.py`

**Intent**: Lossless conversion between aggregates and rows.

**Contract**:
- Each `TypeDecorator` binds the VO's primitive and rebuilds the VO on read. `None` passes through.
- A card with `discard=None` writes three nulls, and three nulls read back as `discard=None`.
- Tag rows are written with `position = enumerate(note.tags)` and read back in `position` order.

#### 2. Repositories

**File**: `backend/src/adapters/out/sqlalchemy/distill/note_repository.py`, `backend/src/adapters/out/sqlalchemy/distill/card_repository.py`

**Intent**: Implement the domain ports inside the caller's transaction, observably identical to the
in-memory adapters.

**Contract**:
- Lookups use `select(Row).where(Row.id == id)`, and note lookups add `selectinload(DistillNoteRow.tags)`.
- `save` inserts a missing row. Otherwise it overwrites every column, and the note repository
  replaces its tag rows. Each write ends with `await session.flush()`, and nothing commits.
- `list_all` orders by `created_at, id`, and `list_by_note` orders by `created_at, id`. Discarded
  cards are included.

#### 3. Contract suites over both implementations

**File**: `backend/tests/unit/distill/contracts/test_note_repository_contract.py`, `backend/tests/unit/distill/contracts/test_card_repository_contract.py`

**Intent**: One suite per port, run in memory on every invocation and on Postgres under the
`postgres` marker.

**Contract**:
- `_IMPLEMENTATIONS` becomes a sync fixture parametrized over `"in_memory"` and
  `pytest.param("postgres", marks=pytest.mark.postgres)`, as in
  `backend/tests/unit/capture/contracts/test_note_repository_contract.py`.
- The Postgres branch takes `engine` through `request.getfixturevalue` and wraps each repository in
  a module-private `_Committing…` class.
- The card suite seeds each card's note through the same implementation's note repository before
  saving cards.

#### 4. Schema constraints

**File**: `backend/tests/integration/postgres/test_distill_schema.py`

**Intent**: Pin the integrity guarantees that only Postgres enforces.

**Contract**: module-level `pytestmark = pytest.mark.postgres`. Rows are inserted through
`SqlAlchemyCardRepository` inside a session, and the test expects `IntegrityError` on flush.

#### Tests

- the note and card contract tests pass with the `postgres` id;
- a note's tags read back in the order they were saved, after a second save reorders them and
  drops one;
- a card's discard reads back equal after a save that adds it to a live card, including a `None`
  detail;
- saving a card whose note does not exist is rejected by Postgres;
- a row with `discard_reason` set but `discarded_at` null is rejected by the `discard_complete`
  CHECK.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/contracts -v` passes with both `in_memory` and
  `postgres` ids
- `cd backend && uv run pytest -m postgres -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Phase 3: Distill query adapter stubs

### Overview

Materialize the three Postgres query adapters that Phase 4's contract suites import.

### Changes Required:

#### 1. Query adapter stubs

**File**: `backend/src/adapters/out/sqlalchemy/distill/list_notes_query.py`, `backend/src/adapters/out/sqlalchemy/distill/get_note_query.py`, `backend/src/adapters/out/sqlalchemy/distill/list_cards_for_note_query.py`

**Intent**: Read models for distill on Postgres, with no aggregate reconstruction.

**Contract**:
- `SqlAlchemyListNotesQueryAdapter`, `SqlAlchemyGetNoteQueryAdapter` and
  `SqlAlchemyListCardsForNoteQueryAdapter`.
- Each has `__init__(self, session_factory: async_sessionmaker[AsyncSession])` and structurally
  satisfies `ListNotesQueryPort`, `GetNoteQueryPort` and `ListCardsForNoteQueryPort` respectively.
- Method bodies raise `NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes

---

## Phase 4: Distill queries on Postgres

### Overview

Implement the three query adapters in SQL. Turn today's in-memory query tests into contract suites
over both implementations.

### Changes Required:

#### 1. List notes

**File**: `backend/src/adapters/out/sqlalchemy/distill/list_notes_query.py`

**Intent**: The note list, with its live-card count and recency computed where the rows live.

**Contract**:
- One statement per call:
  - `distill_notes` left-joined to `distill_cards` with `discard_reason IS NULL`, grouped by note;
  - `card_count = count(card.id)`;
  - `last_updated_at = greatest(note.updated_at, coalesce(max(card.created_at), note.updated_at))`;
  - ordered by `last_updated_at DESC`.
- Rows map straight into `NoteListItemDTO`, with the raw `distillation_status` string.

#### 2. Get note

**File**: `backend/src/adapters/out/sqlalchemy/distill/get_note_query.py`

**Intent**: The note detail read without building a `Note`.

**Contract**:
- Selects the note's columns and its tag rows ordered by `position`. A missing note raises
  `DistillNoteNotFoundError`.
- `blocks` come from `NoteDocument.of(NoteContent(value=content)).blocks`, as in the in-memory
  adapter.

#### 3. List cards for note

**File**: `backend/src/adapters/out/sqlalchemy/distill/list_cards_for_note_query.py`

**Intent**: A note's live cards, with anchor locations, read without building `Card`s.

**Contract**:
- A missing note raises `DistillNoteNotFoundError`.
- Selects live cards (`discard_reason IS NULL`) ordered by `created_at, id`.
- `anchor_location` comes from `NoteDocument.locate(Anchor(quote=anchor_quote))`, mapped as in the
  in-memory adapter's `_to_anchor_location_dto`.

#### 4. Query contract suites

**File**: `backend/tests/unit/distill/contracts/test_list_notes_query_contract.py`, `backend/tests/unit/distill/contracts/test_get_note_query_contract.py`, `backend/tests/unit/distill/contracts/test_list_cards_for_note_query_contract.py`; removes `backend/tests/unit/distill/test_list_notes_query.py` and `backend/tests/unit/distill/test_get_note_query.py`

**Intent**: One suite per query port. The existing in-memory cases become the shared oracle.

**Contract**:
- A fixture parametrized over `"in_memory"` and `pytest.param("postgres", …)` yields the query
  adapter together with a seed that saves notes and cards.
  - In memory, the seed is the in-memory repositories the adapter reads.
  - On Postgres, the seed is committing wrappers over the Phase 2 repositories.
- The existing test functions carry over under their current names.

#### Tests

- every carried-over `list_notes` and `get_note` case passes with the `postgres` id;
- `list_notes` reports a note with no cards at `card_count` 0, with `last_updated_at` equal to the
  note's `updated_at`;
- `get_note` returns tags in their saved order;
- `list_cards_for_note` returns only live cards, ordered by `created_at`;
- `list_cards_for_note` reports an exact block location for a quote equal to a paragraph, and
  `None` for a quote absent from the note;
- `list_cards_for_note` raises `DistillNoteNotFoundError` for an unknown note id.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/contracts -v` passes with both `in_memory` and
  `postgres` ids
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Phase 5: Distill unit of work stub

### Overview

Materialize the SQL `UnitOfWork` that Phase 6's integration tests import.

### Changes Required:

#### 1. SQL unit of work

**File**: `backend/src/adapters/out/sqlalchemy/distill/unit_of_work.py`

**Intent**: Distill's transaction boundary on Postgres, shared with the outbox appender.

**Contract**:
- `class SqlAlchemyDistillUnitOfWork` with
  `__init__(self, session_factory: async_sessionmaker[AsyncSession])`.
- Attributes `notes: SqlAlchemyNoteRepository`, `cards: SqlAlchemyCardRepository` and
  `outbox: SqlAlchemyOutboxAppender`.
- `async def __aenter__(self) -> "SqlAlchemyDistillUnitOfWork"`,
  `async def __aexit__(self, *exc: object) -> None` and `async def commit(self) -> None`.
- Structurally satisfies `application.distill.ports.UnitOfWork`. Bodies raise
  `NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes

---

## Phase 6: Unit of work, atomic commands and the capture-to-cards relay on Postgres

### Overview

Implement the SQL `UnitOfWork`. Prove FR-03 and FR-07 through distill's commands, and the first half
of FR-08 through the real worker and handlers on Postgres.

### Changes Required:

#### 1. Unit of work

**File**: `backend/src/adapters/out/sqlalchemy/distill/unit_of_work.py`

**Intent**: The in-memory UoW's semantics with a real transaction, the same as
`SqlAlchemyCaptureUnitOfWork`.

**Contract**:
- `__aenter__` opens a session from the factory and builds both repositories and
  `SqlAlchemyOutboxAppender` over it.
- `commit` commits.
- `__aexit__` rolls back unless `commit` completed, then closes the session.
- Each `async with` starts from a fresh session.

#### 2. Distill persistence integration tests

**File**: `backend/tests/integration/postgres/test_distill_persistence.py`

**Intent**: FR-03 and FR-07 on distill's own commands, with no HTTP.

**Contract**:
- Module-level `pytestmark = pytest.mark.postgres`. Tests take `engine` and `migrated_database_url`.
- Commands take `uow_factory=lambda: SqlAlchemyDistillUnitOfWork(create_session_factory(engine))`.
- A "fresh engine" is a second `create_engine(migrated_database_url)`, read through new
  repositories.
- Envelopes are observed with `SqlAlchemyOutboxClaimer`.

#### 3. Relay integration test

**File**: `backend/tests/integration/postgres/test_distill_relay.py`

**Intent**: A capture approval becomes a distill note and then its cards, carried only by the
outbox on Postgres (FR-08, first half).

**Contract**:
- The capture side is seeded through `SqlAlchemyCaptureUnitOfWork`, as in
  `test_capture_persistence.py`, and approved with `ApproveNoteCommand`.
- A module-private composition builds `OutboxWorker` from:
  - `SqlAlchemyOutboxClaimer`;
  - handlers `[SaveNoteHandler, FlashcardGenHandler]` over `SqlAlchemyDistillUnitOfWork`;
  - `DeterministicStructuredTaskAdapter`;
  - `CardFactory` and the never-regenerate policy, with the same values as
    `integration/support/in_memory_distill.py`.
- The test runs one `run_once()` and reads results through a fresh engine.

#### Tests

- `SaveNoteCommand` commits the note, readable through a fresh engine, together with one claimable
  `note_saved` envelope carrying its id;
- an exception raised inside the UoW after a note save and an outbox append leaves neither the note
  nor a claimable envelope;
- a discard written by `DiscardCardCommand` reads back equal through a fresh engine;
- after `ApproveNoteCommand` and one `run_once()`, the distill note is `ready` with the approved
  note's id, topic and tags, and it has live cards plus the discarded control card;
- after that same run, no `note_approved` or `note_saved` envelope remains claimable, and `run_once`
  reports both envelopes acked.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration/postgres/test_distill_persistence.py tests/integration/postgres/test_distill_relay.py -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Testing Strategy

### Unit Tests:

- Phase 2 turns the note and card contract suites into fixture-parametrized suites, and the card
  suite seeds notes.
- Phase 4 moves the in-memory query tests into three query contract suites, one of them new for
  `list_cards_for_note`.
- All suites run in memory by default and on Postgres under the `postgres` marker, so
  `-m 'not postgres'` stays database-free.

### Integration Tests:

Three new modules in `tests/integration/postgres/`:
- `test_distill_schema.py` (Phase 2: foreign-key and CHECK rejection);
- `test_distill_persistence.py` (Phase 6: command atomicity and durability);
- `test_distill_relay.py` (Phase 6: capture approval → note → cards through the worker).

The `engine` fixture's post-test `TRUNCATE` cleans every distill table. The HTTP and BDD suites stay
in memory.

### Manual Testing Steps:

1. Upgrade the dev database to head through the adapter's `alembic.ini`.
2. Confirm the three distill tables through the `postgres` MCP server.
3. Downgrade one revision, confirm the distill tables are gone and the capture tables remain, then
   upgrade again.

## Performance Considerations

`list_notes` is one grouped statement over a single user's notes. The `(note_id, created_at)` index
serves both the join and `list_cards_for_note`'s ordering. `GenerateCardsCommand` holds one pooled
connection for its model run, as capture's reply turn does.

## Migration Notes

The distill revision chains onto `2ce37af2f0f8`. The dev database is at the capture head, so
`upgrade head` applies only this revision. `weles_test` is recreated per test session. Moving
`StrEnumType` changes no revision, because migrations render enum columns as `sa.String()`.

## References

- `context/efforts/db-adapter/frame.md` — FR-03, FR-07, FR-08, one revision per surface, no mixed runtime
- `context/efforts/db-adapter/roadmap.md` — slice S-04
- `context/efforts/db-adapter/frame-log.md` — reads outside UoW, parked SQL query adapters
- `context/efforts/db-adapter/research-sql-alchemy.md` — async session, snapshot and composite mapping guidance
- `context/archive/changes/2026-09-13-db-adapter-capture/plan.md` — TypeDecorator, contract seeding, SQL UoW, fresh-engine proof
- `context/archive/changes/2026-09-13-db-adapter-outbox/plan.md` — appender session ownership, claimer
- `context/foundation/rules/cqrs-lite.md`, `context/foundation/rules/contract-testing.md`, `context/foundation/rules/layering.md`
- `context/foundation/testing-conventions.md` — test layout, naming, doubles
