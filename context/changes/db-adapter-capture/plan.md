# Capture Persists in Postgres and Commits Atomically with Its Envelopes — Implementation Plan

Execution state lives in `todos.md` (sibling of this file), per the `/plan` skill's `references/todos-format.md`.

## Overview

Give capture's six repositories and its `UnitOfWork` Postgres implementations, in capture's own
Alembic revision, and prove on real commands that a capture state change and the outbox
envelopes it appends commit or roll back together. This is slice S-03 of effort `db-adapter`. It
delivers FR-02 and FR-07 in tests; the daemon keeps running on in-memory adapters until S-06.

Before any SQL, vocabulary similarity moves behind the repository ports. `TopicRepository` and
`TagRepository` gain `nearest(embedding)`: the adapter computes cosine similarity, and the domain
keeps only the threshold rule. The Postgres adapter then answers `nearest` with pgvector, so
similarity is computed where the embeddings live. `Embedding` also gains the model that produced
it, so a change of embedding model never yields false matches.

## Current State Analysis

- **Ports.** Capture's domain ports live in `backend/src/domain/capture/ports.py`:
  - `CaptureSessionRepository.get/save`, `MessageRepository.add/history`, `NoteRepository.add/get`;
  - `TopicRepository` and `TagRepository` with `add/get/candidates`;
  - `NoteVocabularyRepository.resolve`.

  The application `UnitOfWork` (`backend/src/application/capture/ports.py:14-27`) exposes those
  six repositories plus `outbox: OutboxAppender`.
- **Similarity is computed in the domain today.**
  - `Embedding.cosine_similarity` (`backend/src/domain/capture/value_objects.py`) does max-abs
    scaling, a dimension guard and clamping.
  - `MatchCriteria.best_match` (`backend/src/domain/capture/vocabulary.py:18-37`) scores every
    `candidates()` entry, skips dimension mismatches, and breaks ties by earlier `created_at`.
  - `VocabularyResolver` embeds, calls `candidates()` and asks `best_match`.
  - `capture-flow-domain-shape` (`context/adrs/capture-flow-domain-shape/decision.md:50`) had
    placed similarity search in an outbound port. The archived `capture-flow-tag-dedup` plan moved
    the metric into the domain instead. This plan returns to the ADR's shape.
- **Embedding producers.** `Embedding` has only `values: tuple[float, ...]`.
  `DeterministicEmbeddingAdapter` yields 32 dimensions; `OpenRouterEmbeddingAdapter` yields the
  configured model's (1536 for `openai/text-embedding-3-small`). About 45 `Embedding(values=...)`
  constructions live in 13 test files.
- **In-memory adapters** (`backend/src/adapters/out/in_memory/capture/`) are dict stores.
  `InMemoryUnitOfWork` rolls back by snapshot restore, including the outbox store.
- **Contract suites.** Each of `backend/tests/unit/capture/contracts/test_*_repository_contract.py`
  parametrizes over `_IMPLEMENTATIONS` with only `in_memory`. The message and note suites save
  children for random `SessionId`s with no parent row.
- **S-02 left:**
  - `Base` with a naming convention (`backend/src/adapters/out/sqlalchemy/base.py`), `metadata.py`
    importing model modules, and revision `3b1a9283e2a9` (outbox);
  - `SqlAlchemyOutboxAppender(session)`, which never commits;
  - the shared `engine` / `migrated_database_url` fixtures (`backend/tests/integration/support/postgres.py`),
    whose teardown truncates every public table;
  - the fixture-param contract pattern with a module-private committing wrapper
    (`backend/tests/unit/shared/test_outbox_contract.py`).
- **Commands.**
  - `GenerateReplyCommand.handle` streams the model reply inside `async with self._uow`, adds
    messages, topics, tags and notes during the stream, and saves the session at the end
    (`backend/src/application/capture/commands/send_message.py:78-139`).
  - `ApproveNoteCommand` approves, saves and appends `note_approved` before one commit.
  - A `CoreException` raised during a turn reaches the client as an in-band `ReplyErrorEvent`
    (`backend/src/adapters/http/capture.py:57-62`).
- **Database.** The compose Postgres image is `pgvector/pgvector:pg16`, with extension `vector`
  0.8.6 available; the `pgvector` Python package is not installed.

## Desired End State

Similarity is an adapter concern:
- `TopicRepository.nearest` and `TagRepository.nearest` return the closest comparable entry with
  its `SimilarityScore`;
- `MatchCriteria.accepts` decides whether that score is close enough;
- `Embedding` carries `model` and float32-canonical values.

`backend/src/adapters/out/sqlalchemy/capture/` holds:
- VO column types, where every single-column value object maps through a `TypeDecorator`, so row
  attributes are typed as domain VOs;
- row models;
- six repositories;
- `SqlAlchemyCaptureUnitOfWork`.

One Alembic revision enables `vector` and creates the capture tables. Every capture repository
contract suite passes with both `in_memory` and `postgres` ids. Integration tests on Postgres
prove that:
- state written by `StartCaptureSessionCommand`, `GenerateReplyCommand` and `ApproveNoteCommand`
  survives a fresh engine;
- the approval's envelope commits with the note and session;
- an exception inside the UoW discards state and envelope together;
- a stale session save is rejected with `CaptureSessionConflictError`.

`compose.py` and `main.py` are unchanged.

Verify: `cd backend && uv run pytest` green, `uv run basedpyright` and `uv run ruff check src tests`
clean, and the Phase 3 manual rows.

### Key Discoveries:
- **`composite()` cannot take the Pydantic VOs unchanged.** It needs `__composite_values__()` or a
  dataclass to write, and positional construction to read. An adapter-side VO subclass compares
  unequal to the domain VO (`_LabelC("x") == Label(value="x")` is `False`). A `TypeDecorator[VO]`
  round-trips on the compose Postgres, and `where(Row.id == TagId(...))` binds correctly. Probed on
  SQLAlchemy 2.0.52.
- **`session.get(Row, VO)` fails.** A Pydantic model is iterable, and SQLAlchemy unpacks it as a
  composite key. Lookups by primary key go through `select(...).where(...)`. Probed.
- **pgvector stores float4.** Text output (`0.12345679`) parsed back as float64 does not equal the
  original. Canonicalizing both sides to float32 restores exact equality over 1536 random
  components plus `1e-30` and `3.4e38`. Probed.
- **Cosine in SQL.** An untyped `vector` column holds mixed dimensions. `<=>` raises on mismatched
  dimensions, so `nearest` filters by `vector_dims`.
  `ORDER BY emb <=> :q, created_at LIMIT 1` with `1 - distance` as the score matches the domain's
  tie-break rule. Probed.
- **Exception mapping.** `tests/unit/test_http_error_mapping.py` walks every `CoreException`
  subclass, so each new exception needs an `EXCEPTION_STATUS_MAP` entry in the phase that adds it.
- **Reads outside a UoW** use a short session per call (effort `frame-log.md`, `reads-outside-uow`).
  Wiring that for `guard_session` is composition work and belongs to S-06.

## What We're NOT Doing

- No change to `adapters/compose.py` or `main.py`, and no Postgres composition for HTTP; the
  runtime switch, including the short-session read for `guard_session`, is S-06.
- No re-embedding of stored topics and tags after an embedding-model change. After a switch,
  vocabulary minted under the old model stops matching until a later change re-embeds it from
  labels.
- No vector index: the column has no fixed dimension, and the vocabulary is small.
- No `pgvector` Python dependency; the adapter carries its own `vector` column type.
- No distill or remember tables (S-04, S-05), and no cross-module relay tests.
- No row locks and no advisory locks for capture; concurrency is optimistic only.
- No edit to `context/foundation/testing-conventions.md`.

## Implementation Approach

InMemoryFirst for the port change: Phases 1–2 reshape similarity and `Embedding` and prove them
against the in-memory adapters before any SQL exists. Phases 3–4 add the schema and the six
Postgres repositories, with the existing contract suites as their oracle. Phases 5–6 add the SQL
`UnitOfWork`, optimistic concurrency, and the command-level proof of FR-02 and FR-07.

Session ownership follows S-02:
- every Postgres repository takes the caller's `AsyncSession` and never commits;
- `SqlAlchemyCaptureUnitOfWork` opens one session per `async with`, binds the six repositories and
  `SqlAlchemyOutboxAppender` to it, and owns commit and rollback.

Optimistic concurrency stays inside the adapter, with no domain field:
- `capture_sessions.version` is remembered per session id when a row is read or written through a
  repository instance;
- a later `save` updates only where the version is unchanged;
- a lost race raises `CaptureSessionConflictError`, an application `CoreException` that the HTTP
  layer already turns into a 409 or an in-band `ReplyErrorEvent`.

## Critical Implementation Details

`GenerateReplyCommand` keeps its UoW, and therefore a pooled connection and an open transaction,
for the whole model stream. The version predicate on `save` is what prevents a lost update. Never
take `FOR UPDATE` on the session row, or concurrent turns block each other across streams.

Postgres repositories flush after every write, so foreign-key insert order follows call order. A
turn adds topics and tags before the note that references them, and the session row already
exists before messages are added. `capture_sessions.note_id` deliberately has no foreign key,
because `capture_notes.session_id` already points the other way.

Float32 canonicalization belongs to `Embedding`'s own validation, not to the column type. Only
then does an embedding held in memory equal the same embedding read back from Postgres.

## Phase 1: Similarity port and embedding model stubs

### Overview

Materialize the symbols Phase 2's tests import: `Embedding.model`, the match type in its own
module, `nearest` on both vocabulary ports and in-memory adapters, `MatchCriteria.accepts`, and
the adapter-side cosine helper. Purely additive: `candidates()`, `cosine_similarity` and
`best_match` stay until Phase 2.

### Changes Required:

#### 1. Embedding model and new exceptions

**File**: `backend/src/domain/capture/value_objects.py`, `backend/src/domain/capture/exceptions.py`, `backend/src/adapters/http/errors.py`

**Intent**: An embedding names the model that produced it, because vectors from different models
are not comparable even at equal dimension.

**Contract**:
- `Embedding` gains a required `model: str` field.
- New `EmbeddingComponentOutOfRangeError(CoreException)` and
  `EmptyEmbeddingModelError(CoreException)`, each with an `EXCEPTION_STATUS_MAP` entry carrying
  the same status as the existing `empty_embedding` code.
- Every `Embedding(values=...)` construction in `src` and `tests` passes a model:
  - the deterministic adapter uses `"deterministic-sha512"`;
  - the OpenRouter adapter uses its `model_name`;
  - tests use a module-level literal.

#### 2. Vocabulary match module and ports

**File**: `backend/src/domain/capture/vocabulary_match.py`, `backend/src/domain/capture/vocabulary.py`, `backend/src/domain/capture/ports.py`

**Intent**: Let the ports return a scored entry without a `ports` ↔ `vocabulary` import cycle.

**Contract**:
- `VocabularyMatch[VocabularyEntryT: (Topic, Tag)](BaseModel, frozen=True)` with `entry` and
  `score: SimilarityScore` moves to `vocabulary_match.py`; `vocabulary.py` re-imports it.
- `TopicRepository` gains `async def nearest(self, embedding: Embedding) -> VocabularyMatch[Topic] | None: ...`,
  and `TagRepository` gains the `Tag` equivalent.
- `MatchCriteria` gains `def accepts(self, score: SimilarityScore) -> bool`, whose body raises
  `NotImplementedError`.

#### 3. In-memory stubs

**File**: `backend/src/adapters/out/in_memory/capture/topic_repository.py`, `backend/src/adapters/out/in_memory/capture/tag_repository.py`, `backend/src/adapters/out/in_memory/capture/similarity.py`

**Intent**: Symbols for the contract tests, and a home for the cosine arithmetic that leaves the
domain.

**Contract**:
- `nearest` on `InMemoryTopicRepository` and `InMemoryTagRepository`.
- `def cosine_similarity(left: Embedding, right: Embedding) -> SimilarityScore` in `similarity.py`.

All bodies raise `NotImplementedError`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes

---

## Phase 2: Similarity through the port, in memory

### Overview

Implement `nearest`, the threshold rule and float32 embeddings. Rewire `VocabularyResolver`, and
remove the domain-side metric and `candidates()`.

### Changes Required:

#### 1. Embedding validation

**File**: `backend/src/domain/capture/value_objects.py`, `backend/src/domain/capture/exceptions.py`, `backend/src/adapters/http/errors.py`

**Intent**: One statement of an embedding's precision and validity that every store honours
identically.

**Contract**:
- `values` is canonicalized to float32 (`struct` pack/unpack with `"f"`) after validation.
- A non-finite component, or one whose magnitude exceeds the float32 maximum, raises
  `EmbeddingComponentOutOfRangeError`.
- All-zero components raise `ZeroMagnitudeEmbeddingError`, and empty values still raise
  `EmptyEmbeddingError`.
- `model` is stripped, and a blank model raises `EmptyEmbeddingModelError`.
- `cosine_similarity` and its private helpers leave the domain. `EmbeddingDimensionMismatchError`
  is removed along with its mapping entry.

#### 2. Adapter-side cosine and in-memory `nearest`

**File**: `backend/src/adapters/out/in_memory/capture/similarity.py`, `backend/src/adapters/out/in_memory/capture/topic_repository.py`, `backend/src/adapters/out/in_memory/capture/tag_repository.py`

**Intent**: The in-memory adapter answers the same question the Postgres adapter will.

**Contract**:
- `cosine_similarity` keeps today's arithmetic: max-abs scaling, then clamping into
  `[-1.0, 1.0]`.
- `nearest` considers only entries whose embedding has the same `model` and the same number of
  components.
- It returns the highest-scoring entry with its score, breaking ties by earlier `created_at`, or
  `None` when no entry is comparable.
- `candidates()` is removed from both adapters.

#### 3. Threshold rule and resolver

**File**: `backend/src/domain/capture/vocabulary.py`, `backend/src/domain/capture/ports.py`

**Intent**: The domain keeps what counts as close enough. The port decides which entry is nearest.

**Contract**:
- `MatchCriteria.accepts(score)` returns `score.value >= threshold.value`, and `best_match` is
  removed.
- `VocabularyResolver` embeds the label and calls `nearest`. It reuses `match.entry` when
  `accepts(match.score)`, and otherwise mints and adds.
- `ResolvedTopic` and `ResolvedTag` are unchanged, and `candidates()` leaves both protocols.

#### 4. Tests reshaped

**File**: `backend/tests/unit/capture/test_vocabulary_matching.py`, `backend/tests/unit/capture/contracts/test_topic_repository_contract.py`, `backend/tests/unit/capture/contracts/test_tag_repository_contract.py`, `backend/tests/unit/capture/test_unit_of_work.py`, `backend/tests/unit/capture/test_value_objects.py`

**Intent**: Behaviour previously pinned on the domain metric is pinned where it now lives.

**Contract**:
- The `candidates()` contract cases become `nearest` cases, and the cosine unit cases move to the
  in-memory similarity helper.
- `test_rollback_without_commit_excludes_topics_and_tags_from_candidates` becomes
  `test_rollback_without_commit_leaves_no_topic_or_tag_to_find_as_nearest`.

#### Tests

- an embedding's components equal their float32 values after construction, so an embedding
  rebuilt from its own float32 components is equal to it;
- an embedding with a component beyond the float32 range, or with only zero components, is rejected
  at construction;
- `nearest` returns the highest-scoring entry with its score and breaks equal scores by earlier
  `created_at` (topic and tag contracts);
- `nearest` ignores entries embedded by another model or with another dimension, and returns `None`
  when nothing comparable is stored (topic and tag contracts);
- `MatchCriteria` accepts a score equal to the threshold and rejects one just below it;
- the resolver reuses a stored topic only when its nearest score clears the threshold, and otherwise
  mints and adds one.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Phase 3: Capture schema and Postgres repository stubs

### Overview

Create the capture tables and the `vector` extension in capture's revision, and materialize the VO
column types, row models and six repository classes.

### Changes Required:

#### 1. VO column types

**File**: `backend/src/adapters/out/sqlalchemy/capture/__init__.py`, `backend/src/adapters/out/sqlalchemy/capture/types.py`

**Intent**: Row attributes typed as the domain's value objects, so the schema cannot drift from
them.

**Contract**:
- `TypeDecorator` subclasses (`cache_ok = True`):
  - `SessionIdType`, `MessageIdType`, `NoteIdType`, `TopicIdType` and `TagIdType` over
    `UUID(as_uuid=True)`;
  - `SessionTopicType`, `LabelType`, `MessageContentType` and `NoteContentType` over `String` /
    `Text`;
  - `StrEnumType(enum_cls)` over `String`;
  - `CoverageHistoryType`, `tuple[Coverage, ...]` over `ARRAY(Double)`;
  - `DraftingConsentType` and `ConversationRequestType`, `VO | None` over non-null `Boolean`.
- `VectorType`: a `UserDefinedType` with column spec `vector`. It binds a float sequence as the
  `[a,b,...]` literal and parses the text result to `tuple[float, ...]`.
- Bodies raise `NotImplementedError`.

#### 2. Row models

**File**: `backend/src/adapters/out/sqlalchemy/capture/models.py`, `backend/src/adapters/out/sqlalchemy/capture/mapping.py`, `backend/src/adapters/out/sqlalchemy/metadata.py`

**Intent**: Capture's full state in normalized tables with referential integrity.

**Contract**:
- `CaptureSessionRow`, table `capture_sessions`:
  - `id` PK; `topic` null; `note_id` null, with no FK;
  - `status` and `phase` with CHECKs;
  - `drafting_consent` and `conversation_request` BOOLEAN not null;
  - `assessments` DOUBLE PRECISION[] not null;
  - `created_at` TIMESTAMPTZ; `version` INTEGER not null.
- `CaptureMessageRow`, table `capture_messages`:
  - `id` PK; `position` BIGINT identity, unique;
  - `session_id` FK → `capture_sessions.id`;
  - `role` with a CHECK; `content` TEXT; `created_at`;
  - index on `(session_id, position)`.
- `CaptureTopicRow` (`capture_topics`) and `CaptureTagRow` (`capture_tags`): `id` PK, `label`,
  `embedding_values` `vector` not null, `embedding_model` VARCHAR not null, `created_at`.
- `CaptureNoteRow`, table `capture_notes`:
  - `id` PK; `session_id` FK → `capture_sessions.id`; `topic_id` FK → `capture_topics.id`;
  - `content` TEXT; `status` with a CHECK; `created_at`; `approved_at` null;
  - relationship `tags` to `CaptureNoteTagRow`, ordered by `position`, `cascade="all, delete-orphan"`.
- `CaptureNoteTagRow`, table `capture_note_tags`: `note_id` FK → `capture_notes.id` ON DELETE
  CASCADE, `position` INTEGER, `tag_id` FK → `capture_tags.id`, PK `(note_id, position)`.
- `mapping.py` declares `to_row` / `to_domain` pairs per aggregate. `Embedding` spans two columns
  and is assembled there, because `composite()` cannot build the Pydantic VO. Bodies raise
  `NotImplementedError`.
- `metadata.py` imports the capture models module.

#### 3. Capture revision

**File**: `backend/src/adapters/out/sqlalchemy/migrations/versions/<rev>_create_capture_tables.py`

**Intent**: Capture's own revision (effort boundary: one revision per surface).

**Contract**:
- `down_revision = "3b1a9283e2a9"`.
- Produced with `alembic -c src/adapters/out/sqlalchemy/alembic.ini revision --autogenerate -m "create capture tables"`,
  then reviewed by hand.
- `upgrade` starts with `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`. The revision
  imports `VectorType` from `adapters.out.sqlalchemy.capture.types` for the two `embedding_values`
  columns, because autogenerate cannot render the custom type unaided. Every other VO column is
  rendered with its underlying `impl` type.
- `downgrade` drops the six tables in dependency order, then runs
  `DROP EXTENSION IF EXISTS vector`.

#### 4. Repository stubs

**File**: `backend/src/adapters/out/sqlalchemy/capture/capture_session_repository.py`, `message_repository.py`, `note_repository.py`, `topic_repository.py`, `tag_repository.py`, `note_vocabulary_repository.py` (same directory)

**Intent**: Symbols the Phase 4 contract tests import.

**Contract**:
- `SqlAlchemyCaptureSessionRepository`, `SqlAlchemyMessageRepository`,
  `SqlAlchemyNoteRepository`, `SqlAlchemyTopicRepository`, `SqlAlchemyTagRepository` and
  `SqlAlchemyNoteVocabularyRepository`.
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
  on the dev database, and `… current` prints the capture revision as head
- Through the `postgres` MCP server, `select extname from pg_extension where extname = 'vector'`
  returns one row, and `select table_name from information_schema.tables where table_name like 'capture_%'`
  lists the six capture tables
- `… downgrade -1` exits 0, and the MCP server no longer finds the capture tables or the `vector`
  extension; `… upgrade head` restores them

---

## Phase 4: Capture repositories on Postgres

### Overview

Implement the column types, mapping and six repositories until every capture contract suite passes
on Postgres.

### Changes Required:

#### 1. Column types and mapping

**File**: `backend/src/adapters/out/sqlalchemy/capture/types.py`, `backend/src/adapters/out/sqlalchemy/capture/mapping.py`

**Intent**: Lossless conversion between aggregates and rows.

**Contract**:
- Each `TypeDecorator` binds the VO's primitive and rebuilds the VO on read; `None` passes through
  where the column is nullable.
- The consent and request types bind `value is not None` and read `True` as the VO instance.
- `VectorType` output is rebuilt into `Embedding(values=..., model=row.embedding_model)`, which
  re-canonicalizes to float32.

#### 2. Repositories

**File**: the six repository modules under `backend/src/adapters/out/sqlalchemy/capture/`

**Intent**: Implement the domain ports inside the caller's transaction, observably identical to
the in-memory adapters.

**Contract**:
- Lookups use `select(Row).where(Row.id == id)`, never `session.get`.
- Every write ends with `await session.flush()`, and nothing commits.
- `save`, and `add` on the note, topic and tag repositories, overwrite an existing row by id.
  - The session repository inserts with `version = 1`, and otherwise updates and increments
    `version`, with no predicate yet.
  - The note repository replaces its `capture_note_tags` rows in `tag_ids` order.
- `history` orders by `position`.
- `nearest` selects:
  - `WHERE embedding_model = :model AND vector_dims(embedding_values) = :dims`;
  - `ORDER BY embedding_values <=> :q, created_at LIMIT 1`;
  - the score as `1 - distance`, clamped into `[-1.0, 1.0]` and wrapped in `SimilarityScore`.
- `resolve` loads the topic and the note's tags by id and returns them in `tag_ids` order. It
  raises `NoteVocabularyIncompleteError` when any is missing.

#### 3. Contract suites over both implementations

**File**: `backend/tests/unit/capture/contracts/test_capture_session_repository_contract.py`, `test_message_repository_contract.py`, `test_note_repository_contract.py`, `test_topic_repository_contract.py`, `test_tag_repository_contract.py`, `test_note_vocabulary_repository_contract.py`

**Intent**: One suite per port, run in memory on every invocation and on Postgres under the
`postgres` marker.

**Contract**:
- Each `_IMPLEMENTATIONS` list becomes a sync fixture parametrized over `"in_memory"` and
  `pytest.param("postgres", marks=pytest.mark.postgres)`, as in `test_outbox_contract.py`.
- The Postgres branch takes `engine` through `request.getfixturevalue`. It wraps the repository in
  a module-private `_Committing…` adapter that opens a session, delegates and commits.
- The message and note suites seed their parent session (and the note's topic and tags) through
  the same implementation before adding children.
- `test_add_persists_message_visible_via_the_shared_store` becomes
  `test_added_message_is_in_history_read_through_another_repository_instance`.

#### Tests

- every capture repository contract test passes with the `postgres` id, including `nearest`
  skipping other models and dimensions;
- a note's tags read back in the order they were attached, after a second `add` reorders them;
- message history reads back in insertion order when two messages share a `created_at`;
- a capture session's assessments, phase, consent and conversation request read back equal after
  an overwrite;
- adding a message whose session row does not exist is rejected by Postgres
  (`backend/tests/integration/postgres/test_capture_schema.py`).

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/capture/contracts -v` passes with both `in_memory` and
  `postgres` ids
- `cd backend && uv run pytest -m postgres -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Phase 5: Capture unit of work and conflict stubs

### Overview

Materialize the SQL `UnitOfWork` and the conflict exception that Phase 6's tests import.

### Changes Required:

#### 1. SQL unit of work

**File**: `backend/src/adapters/out/sqlalchemy/capture/unit_of_work.py`

**Intent**: Capture's transaction boundary on Postgres, shared with the outbox appender.

**Contract**:
- `class SqlAlchemyCaptureUnitOfWork` with
  `__init__(self, session_factory: async_sessionmaker[AsyncSession])`.
- Attributes typed as the six `SqlAlchemy…Repository` classes plus
  `outbox: SqlAlchemyOutboxAppender`.
- `async def __aenter__(self) -> "SqlAlchemyCaptureUnitOfWork"`,
  `async def __aexit__(self, *exc: object) -> None` and `async def commit(self) -> None`.
- Structurally satisfies `application.capture.ports.UnitOfWork`. Bodies raise
  `NotImplementedError`.

#### 2. Conflict exception

**File**: `backend/src/application/capture/exceptions.py`, `backend/src/adapters/http/errors.py`

**Intent**: A named outcome for losing an optimistic race on a capture session.

**Contract**: `class CaptureSessionConflictError(CoreException)`, code `capture_session_conflict`,
mapped to `409` in `EXCEPTION_STATUS_MAP`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright` clean
- `cd backend && uv run ruff check src tests` clean
- `cd backend && uv run pytest -m 'not postgres'` passes

---

## Phase 6: Unit of work, optimistic concurrency and atomic commands on Postgres

### Overview

Implement the SQL `UnitOfWork` and the version predicate. Prove FR-02 and FR-07 through the real
capture commands on Postgres.

### Changes Required:

#### 1. Unit of work

**File**: `backend/src/adapters/out/sqlalchemy/capture/unit_of_work.py`

**Intent**: The in-memory UoW's semantics with a real transaction.

**Contract**:
- `__aenter__` opens a session from the factory and builds the six repositories and
  `SqlAlchemyOutboxAppender` over it.
- `commit` commits.
- `__aexit__` rolls back unless `commit` completed, then closes the session.
- Each `async with` starts from a fresh session.

#### 2. Optimistic session save

**File**: `backend/src/adapters/out/sqlalchemy/capture/capture_session_repository.py`

**Intent**: A turn or approval that lost a race fails loudly instead of overwriting the winner.

**Contract**:
- The repository remembers the `version` of every session row it reads or writes.
- `save` of a remembered id runs `UPDATE … SET …, version = :v + 1 WHERE id = :id AND version = :v`.
  When no row matches, it raises `CaptureSessionConflictError`.
- `save` of an id it has never seen inserts with `version = 1`.

#### 3. Capture persistence integration tests

**File**: `backend/tests/integration/postgres/test_capture_persistence.py`

**Intent**: FR-02 and FR-07 on the real commands, with no HTTP.

**Contract**:
- Module-level `pytestmark = pytest.mark.postgres`; tests take `engine` and `migrated_database_url`.
- Commands are composed in the test with:
  - `SqlAlchemyCaptureUnitOfWork(create_session_factory(engine))`;
  - `DeterministicCaptureAgentAdapter`;
  - `VocabularyResolver(DeterministicEmbeddingAdapter(), MatchCriteria(...))`.
- A "fresh engine" is a second `create_engine(migrated_database_url)`, read through new
  repositories.
- Envelopes are observed with `SqlAlchemyOutboxClaimer`.

#### Tests

- a session started by `StartCaptureSessionCommand` reads back equal through a fresh engine;
- a `GenerateReplyCommand` turn that drafts a note leaves its messages, note, topic and tags
  readable through a fresh engine;
- `ApproveNoteCommand` commits the approved note, the closed session and one claimable
  `note_approved` envelope together;
- an exception raised inside the UoW after a session save, a note add and an outbox append leaves
  none of them persisted;
- saving a session that a concurrent UoW saved and committed after it was read raises
  `CaptureSessionConflictError`, and the concurrent write is what reads back.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration/postgres/test_capture_persistence.py -v` passes
- `cd backend && uv run pytest` passes
- `cd backend && uv run basedpyright` and `uv run ruff check src tests` clean

---

## Testing Strategy

### Unit Tests:

- Phase 2 moves similarity coverage from the domain metric to the in-memory helper and the
  `nearest` contract.
- Phase 2 adds float32 and range cases for `Embedding` and the `accepts` rule.
- Phase 4 turns the six capture contract suites into fixture-parametrized suites. They run in
  memory by default and on Postgres under the `postgres` marker, so `-m 'not postgres'` stays
  database-free.

### Integration Tests:

Two new modules in `tests/integration/postgres/`:
- `test_capture_schema.py` (Phase 4, foreign-key rejection);
- `test_capture_persistence.py` (Phase 6, five command and UoW tests).

Both run on real commits, and the `engine` fixture's post-test `TRUNCATE` cleans every capture
table.

### Manual Testing Steps:

1. Upgrade the dev database to head through the adapter's `alembic.ini`.
2. Confirm the `vector` extension and the six capture tables through the `postgres` MCP server.
3. Downgrade one revision, confirm they are gone, and upgrade again.

## Performance Considerations

`nearest` scans a model's comparable rows without an index. That is acceptable for a single
user's vocabulary, and an index needs a fixed dimension this change deliberately avoids. A turn
holds one pooled connection for its model stream.

## Migration Notes

The capture revision chains onto `3b1a9283e2a9`. The dev database is at the outbox head, so
`upgrade head` applies only this revision. `weles_test` is recreated per test session. The compose
image already ships pgvector, and the migration role can create the extension (probed on
`weles_test`).

## References

- `context/efforts/db-adapter/frame.md` — FR-02, FR-07, one revision per surface, no mixed runtime
- `context/efforts/db-adapter/roadmap.md` — slice S-03
- `context/efforts/db-adapter/frame-log.md` — parked capture concurrency, embeddings storage, reads outside UoW
- `context/efforts/db-adapter/research-sql-alchemy.md` — async session, composite and mapping guidance
- `context/archive/changes/2026-09-13-db-adapter-outbox/plan.md` — appender session ownership, contract fixture pattern
- `context/archive/changes/2026-09-01-capture-flow-tag-dedup/plan.md` — the domain-side metric this plan moves behind the port
- `context/adrs/capture-flow-domain-shape/decision.md` — similarity search in an outbound port
- `context/foundation/rules/contract-testing.md`, `context/foundation/rules/layering.md`, `context/foundation/rules/exceptions.md`
- `context/foundation/testing-conventions.md` — test layout, naming, doubles
- <https://docs.sqlalchemy.org/en/20/core/custom_types.html#augmenting-existing-types> — `TypeDecorator`
- <https://github.com/pgvector/pgvector#querying> — `<=>` cosine distance, `vector_dims`
