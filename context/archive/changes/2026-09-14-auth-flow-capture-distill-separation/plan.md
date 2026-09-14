# Capture and Distill Separation Implementation Plan

## Overview

Make every capture session, capture note, topic, tag, distill note, and card belong to the person who signed in when it was created, and make every read or write reachable from HTTP refuse data belonging to anyone else. Ownership travels from the sign-in gate's `UserId` into the capture session, across the `note_approved` envelope into distill, and onto the cards generated in the background. Realizes AC-15 (`context/efforts/auth-flow/stories.md`, US-06) and the capture/distill half of PRD FR-008. Remember keeps reading across people until S-05 (`context/efforts/auth-flow/roadmap.md`, S-04).

Execution state lives in `todos.md`.

## Current State Analysis

S-01 (`context/archive/changes/2026-09-14-auth-flow-sign-in-gate/`) left this in place:

- `UserId` in `backend/src/domain/shared/identity/model.py`, documented as the key S-04 and S-05 attach data to.
- `require_sign_in` returns a `UserId` (`backend/src/adapters/auth/router.py:31-45`). The `gated` router in `backend/src/main.py:40` depends on it, but no route reads the value and no handler receives it.

The core has no ownership anywhere:

- No aggregate carries an owner: `CaptureSession`, capture `Note`, `Topic`, `Tag`, distill `Note`, `Card`.
- `TopicRepository.nearest` and `TagRepository.nearest` match against every entry on the instance, so another person's topic label can be offered as a reuse match.
- `NoteApprovedPayload` carries no owner, so distill cannot learn whose note it mints.
- The three distill query ports (`list_notes`, `get_note`, `list_cards_for_note`) return every note and card on the instance.
- No capture or distill table has an owner column. The Alembic head is `d4e8f1a29b3c` (`auth_accounts`).

Test fixtures that bypass the gate return a fresh `UserId.new()` on every request. Once handlers compare owners, a session created by one request would belong to a different person than the next request.

## Desired End State

- A signed-in person gets `404 capture_session_not_found` for another person's capture session, on the message stream guard, on the message stream, and on approval. The response is identical to an unknown id.
- Topic and tag reuse during drafting only ever matches the drafting person's own vocabulary.
- A note approved by a person reaches distill stamped with that person, and every card generated from it carries the same owner (AC-15).
- `GET /notes` lists only the caller's notes. `GET /notes/{id}` and `GET /notes/{id}/cards` answer `404 distill_note_not_found` for another person's note.
- `capture_sessions`, `capture_notes`, `capture_topics`, `capture_tags`, `distill_notes`, and `distill_cards` carry `owner_id UUID NOT NULL`, added by two chained Alembic revisions.

Verify with:

- `cd backend && uv run pytest -m "not postgres"`
- `cd backend && uv run pytest -m postgres` (with `TEST_DATABASE_URL`)
- `cd backend && uv run basedpyright`

### Key Discoveries:

- `backend/src/adapters/auth/router.py:31`: `require_sign_in` is the one dependency every override keys on. A route that declares `Annotated[UserId, Depends(require_sign_in)]` reuses FastAPI's per-request dependency cache, so the gated router's own dependency and the route's parameter verify the token once.
- `backend/tests/integration/conftest.py:55`, `backend/tests/bdd/conftest.py:50`, and `backend/tests/integration/test_capture_http.py:347` override the gate with a new `UserId` per call.
- `backend/src/application/capture/commands/send_message.py` (`_get_open_session`) is the single session-loading choke point for both `guard_session` and `handle`. `approve_note.py` loads the session separately.
- Messages, the capture note, and a note's topic and tags are reached only through a session or a note already loaded (`send_message.py`, `approve_note.py`, `note_vocabulary_repository.py`). The session is therefore the only capture aggregate that needs an ownership check.
- `backend/src/domain/capture/graph.py:415,431`: the vocabulary resolver is called from graph actions that hold `context.session`, which is where the owner for `nearest` and `mint` comes from.
- `backend/src/domain/distill/run.py:128`: cards are minted through `card_factory.mint(self.note.id, …)`, so the run's note supplies the card owner.
- Distill commands (`SaveNoteCommand`, `GenerateCardsCommand`, `DiscardCardCommand`) are reached only from outbox handlers, never from HTTP. Ownership in distill therefore rides on data, not on a caller.
- `distill.NoteRepository.list_all` is called only by two adapters: `adapters/out/in_memory/distill/list_notes_query.py:14` and `adapters/out/in_memory/remember/review_catalog.py:33`. No application code calls it.
- `backend/src/adapters/http/errors.py:8,45`: `capture_session_not_found` and `distill_note_not_found` already map to 404, so no new exception or mapping is needed.
- `backend/tests/unit/distill/contracts/test_list_notes_query_contract.py:114`, `test_get_note_query_contract.py:67`, `test_list_cards_for_note_query_contract.py:121`, and `backend/tests/unit/capture/contracts/test_tag_repository_contract.py:36` are already parametrized `in_memory` and `postgres`. New cases join these suites.
- `backend/src/adapters/compose.py`: query adapters and resolvers are process-wide singletons. They stay singletons, because the owner arrives as a call argument and nothing per-request is stored on them.

## What We're NOT Doing

- Remember in any form: `ReviewCatalog`, `CardSourceLocator`, `SittingReader.latest`, the remember lock, and the owner of `card_rejected` → `DiscardCardCommand`. All of this belongs to S-05.
- Scoping `distill.NoteRepository.list_all`. It stays unscoped for the in-memory remember catalog until S-05 replaces that caller.
- Owner columns on `capture_messages`, `capture_note_tags`, or `distill_note_tags`. They are reachable only through an owned parent.
- Ownership checks inside distill commands. Their only callers are outbox handlers.
- New exception classes or a 403 response. A foreign id is not found.
- Backfilling or reassigning existing rows (PRD Non-Goals).
- TUI changes. No response shape changes.
- Acceptance scenarios. AC-15 scenarios come from `/bdd auth-flow-capture-distill-separation`, not from these phases.
- The uncommitted edit in `backend/src/adapters/compose.py`. It is not part of this change and is never staged by it.

## Implementation Approach

The work goes context by context, following the data: capture first, because distill learns the owner from capture's envelope. Each context is a stubs-then-behavior pair:

- **Stubs phase.** Materializes every ownership symbol: fields, factory and port signatures, command signatures, ORM columns, the Alembic revision, and route parameters. It also stamps the owner wherever an object is created from a parent that already has one, since a valid object cannot be built without it. Every *exclusion* stays unimplemented: repositories and query adapters accept the owner and ignore it (`_ = owner`), and commands do not compare it. The suite ends green with existing tests threaded through the new signatures.
- **Behavior phase.** Adds the exclusions behind tests written first.

Enforcement follows the session's choice:

- A command that loads an aggregate by id compares `aggregate.owner_id` with the caller in the application handler and raises the existing not-found error.
- Collective reads (`nearest`) and CQRS-lite query ports take the owner and filter at the source.

## Critical Implementation Details

The gate override in every HTTP and BDD fixture must return one `UserId` fixed for the fixture's lifetime. This change lands in Phase 1, while ownership is still ignored. Otherwise every multi-request test goes red in Phase 2 for a reason unrelated to its subject.

The foreign-owner check in `_get_open_session` and `ApproveNoteCommand` runs before the closed-session and missing-draft checks. Otherwise another person's closed session answers `409 capture_session_closed` and confirms that the session exists.

## Phase 1: Capture ownership symbols

### Overview

Put the owner on every capture aggregate, port, command, table, and route, stamped from the session outward. Nothing is excluded yet.

### Changes Required:

#### 1. Capture domain ownership

**File**: `backend/src/domain/capture/capture_session.py`, `backend/src/domain/capture/note.py`, `backend/src/domain/capture/topic.py`, `backend/src/domain/capture/tag.py`, `backend/src/domain/capture/ports.py`, `backend/src/domain/capture/vocabulary.py`, `backend/src/domain/capture/graph.py`, `backend/src/domain/capture/outbox.py`

**Intent**: Every capture object knows its owner, and the owner flows from the session into what the session creates.

**Contract**:
- `CaptureSession.owner_id: UserId` and `CaptureSession.start(owner: UserId)`.
- Capture `Note.owner_id: UserId` and `Note.draft(owner_id, session_id, topic, content, tags)`. `CaptureSession.draft_note` passes `self.owner_id`.
- `Topic.owner_id` with `Topic.mint(owner, label, embedding)`, and `Tag.owner_id` with `Tag.mint(owner, label, embedding)`.
- `TopicRepository.nearest(owner: UserId, embedding)` and `TagRepository.nearest(owner: UserId, embedding)`.
- `VocabularyResolver.resolve_topic(owner, label, topics)` and `resolve_tag(owner, label, tags)` pass the owner to `nearest` and `mint`. The graph actions `_resolve_note_topic` and `_resolve_note_tag` pass `context.session.owner_id`.
- `NoteApprovedPayload.owner_id: UUID`, filled from `note.owner_id` in `NoteApprovedPayload.of`.

#### 2. Capture command signatures

**File**: `backend/src/application/capture/commands/start_capture_session.py`, `backend/src/application/capture/commands/send_message.py`, `backend/src/application/capture/commands/approve_note.py`

**Intent**: The person arrives as an explicit input to every capture command. No ambient current-user reader is introduced.

**Contract**:
- `StartCaptureSessionCommand.handle(owner: UserId)` starts the session for `owner`.
- `GenerateReplyCommand.guard_session(owner, session_id, raw_content)`, `GenerateReplyCommand.handle(owner, session_id, content)`, and `ApproveNoteCommand.handle(owner, session_id)`. `owner` is accepted but not yet compared.

#### 3. Capture persistence

**File**: `backend/src/adapters/out/sqlalchemy/capture/models.py`, `backend/src/adapters/out/sqlalchemy/capture/mapping.py`, `backend/src/adapters/out/sqlalchemy/capture/topic_repository.py`, `backend/src/adapters/out/sqlalchemy/capture/tag_repository.py`, `backend/src/adapters/out/sqlalchemy/capture/capture_session_repository.py`, `backend/src/adapters/out/sqlalchemy/capture/note_repository.py`, `backend/src/adapters/out/in_memory/capture/topic_repository.py`, `backend/src/adapters/out/in_memory/capture/tag_repository.py`, `backend/src/adapters/out/sqlalchemy/migrations/versions/<rev>_add_owner_to_capture_tables.py`

**Intent**: The owner survives a round trip through both adapters. The table shape is final in this phase.

**Contract**:
- `owner_id` (UUID, not null) on `CaptureSessionRow`, `CaptureNoteRow`, `CaptureTopicRow`, and `CaptureTagRow`, with an index on `owner_id` for topics and tags.
- The mappers carry `owner_id` in both directions. The session and note repositories write it on insert and never update it.
- Both `nearest` implementations accept `owner` and ignore it (`_ = owner`).
- Migration: `down_revision = "d4e8f1a29b3c"`. It adds the four columns as `NOT NULL` with no server default and `op.f` index names. `downgrade` drops the indexes and columns.

#### 4. Capture routes and gate fixtures

**File**: `backend/src/adapters/http/capture.py`, `backend/tests/integration/conftest.py`, `backend/tests/bdd/conftest.py`, `backend/tests/integration/test_capture_http.py`

**Intent**: The gate's `UserId` reaches the capture commands, and test clients act as one stable person.

**Contract**:
- `get_turn_context`, `start_capture_session`, `send_message`, and `approve_note` declare `user_id: Annotated[UserId, Depends(require_sign_in)]` and pass it as `owner`.
- Every fixture that overrides `require_sign_in` creates one `UserId.new()` per fixture instance and returns that value on every call.
- Existing capture unit, contract, integration, and BDD step call sites are threaded with an owner and assert nothing new.

### Success Criteria:

#### Automated Verification:
- Offline backend suite passes: `cd backend && uv run pytest -m "not postgres"`
- Postgres lane passes: `cd backend && uv run pytest -m postgres`
- Type check passes: `cd backend && uv run basedpyright`

#### Manual Verification:
- Against an emptied dev database, run `cd backend && uv run alembic upgrade head`, then `uv run alembic downgrade -1`, then `uv run alembic upgrade head`. All three succeed, and `capture_sessions.owner_id` exists and is `NOT NULL` at the end.

---

## Phase 2: Capture separation

### Overview

Make capture refuse another person's session and match only the drafting person's vocabulary.

### Changes Required:

#### 1. Vocabulary matching per person

**File**: `backend/src/adapters/out/in_memory/capture/topic_repository.py`, `backend/src/adapters/out/in_memory/capture/tag_repository.py`, `backend/src/adapters/out/sqlalchemy/capture/topic_repository.py`, `backend/src/adapters/out/sqlalchemy/capture/tag_repository.py`, `backend/tests/unit/capture/contracts/test_topic_repository_contract.py`, `backend/tests/unit/capture/contracts/test_tag_repository_contract.py`

**Intent**: A label from another person's notes is never offered for reuse.

**Contract**:
- `nearest(owner, embedding)` considers only entries whose `owner_id == owner`. The SQL statement adds `owner_id == owner.value` to its `where` clause.
- In both contract suites, another owner's entry is ignored even when it is the closest match, and `None` is returned when only other owners have entries.

#### 2. Session ownership in commands

**File**: `backend/src/application/capture/commands/send_message.py`, `backend/src/application/capture/commands/approve_note.py`, `backend/tests/unit/capture/test_send_message_command.py`, `backend/tests/unit/capture/test_approve_note_command.py`

**Intent**: Another person's session is indistinguishable from a session that does not exist.

**Contract**:
- `_get_open_session(capture_sessions, owner, session_id)` raises `CaptureSessionNotFoundError` when the session is missing or `session.owner_id != owner`, before the closed check.
- `ApproveNoteCommand.handle` applies the same check before `SessionNoteMissingError`.

#### 3. Two people over HTTP

**File**: `backend/tests/integration/test_capture_http.py`

**Intent**: Prove the router hands the gate's person to the commands.

**Contract**: A module-private switchable identity override. A session started as person A answers 404 `capture_session_not_found` to person B, both on a message and on approval.

### Success Criteria:

#### Automated Verification:
- Capture contracts pass in memory: `cd backend && uv run pytest tests/unit/capture/contracts -m "not postgres" -v`
- Capture contracts pass on Postgres: `cd backend && uv run pytest tests/unit/capture/contracts -m postgres -v`
- Capture unit and HTTP tests pass: `cd backend && uv run pytest tests/unit/capture tests/integration/test_capture_http.py -v`
- Full offline suite passes: `cd backend && uv run pytest -m "not postgres"`
- Type check passes: `cd backend && uv run basedpyright`

#### Manual Verification:
- With the backend running, register and sign in persons A and B through `POST /auth/register` and `POST /auth/sign-in`.
- `curl -X POST localhost:8000/capture-sessions -H "Authorization: Bearer <A>"` returns a session id.
- `curl -i -X POST localhost:8000/capture-sessions/<id>/approval -H "Authorization: Bearer <B>"` answers 404 `capture_session_not_found`.
- The same call with A's token answers 409 `session_note_missing`.

---

## Phase 3: Distill ownership symbols

### Overview

Carry the owner from the approval envelope onto distill notes and cards, and put it on the query ports, tables, and routes. Nothing is excluded yet.

### Changes Required:

#### 1. Distill domain ownership

**File**: `backend/src/domain/distill/note.py`, `backend/src/domain/distill/card.py`, `backend/src/domain/distill/card_factory.py`, `backend/src/domain/distill/run.py`

**Intent**: A distill note and every card generated from it know their owner (AC-15).

**Contract**:
- Distill `Note.owner_id: UserId` and `mint_note(owner_id, note_id, session_id, topic, content, tags, approved_at)`.
- `Card.owner_id: UserId` and `CardFactory.mint(owner_id, note_id, front, back, anchor, resolution)`. `DistillRun` passes `self.note.owner_id`.

#### 2. Distill command, handler, and query port signatures

**File**: `backend/src/application/distill/commands/save_note.py`, `backend/src/adapters/out/worker/handlers/note_save.py`, `backend/src/application/distill/queries/list_notes.py`, `backend/src/application/distill/queries/get_note.py`, `backend/src/application/distill/queries/list_cards_for_note.py`

**Intent**: Ownership crosses the outbox as data, and the queries accept the person they will later filter by.

**Contract**:
- `SaveNoteCommand.handle(owner_id: UserId, note_id, …)` mints the note for `owner_id`.
- `SaveNoteHandler` passes `UserId(value=payload.owner_id)`. An envelope without `owner_id` fails validation and follows the existing malformed-envelope path.
- `ListNotesQueryPort.list_notes(owner)`, `GetNoteQueryPort.get_note(owner, note_id)`, and `ListCardsForNoteQueryPort.list_cards_for_note(owner, note_id)`.

#### 3. Distill persistence and query adapters

**File**: `backend/src/adapters/out/sqlalchemy/distill/models.py`, `backend/src/adapters/out/sqlalchemy/distill/mapping.py`, `backend/src/adapters/out/sqlalchemy/distill/note_repository.py`, `backend/src/adapters/out/sqlalchemy/distill/card_repository.py`, `backend/src/adapters/out/sqlalchemy/distill/list_notes_query.py`, `backend/src/adapters/out/sqlalchemy/distill/get_note_query.py`, `backend/src/adapters/out/sqlalchemy/distill/list_cards_for_note_query.py`, `backend/src/adapters/out/in_memory/distill/list_notes_query.py`, `backend/src/adapters/out/in_memory/distill/get_note_query.py`, `backend/src/adapters/out/in_memory/distill/list_cards_for_note_query.py`, `backend/src/adapters/out/sqlalchemy/migrations/versions/<rev>_add_owner_to_distill_tables.py`

**Intent**: The owner survives both adapters, and the query adapters take the new signatures.

**Contract**:
- `owner_id` (UUID, not null) on `DistillNoteRow` (indexed) and `DistillCardRow`.
- The mappers carry `owner_id` both ways, and the repositories write it on insert.
- All six query adapters accept `owner` and ignore it (`_ = owner`).
- Migration: `down_revision` is the Phase 1 revision. It adds both columns `NOT NULL` with no default, and `downgrade` drops them.

#### 4. Notes routes and test factories

**File**: `backend/src/adapters/http/notes.py`, test modules that construct distill `Note` or `Card` (`backend/tests/unit/distill/`, `backend/tests/unit/remember/`, `backend/tests/integration/`, `backend/tests/bdd/`)

**Intent**: The gate's person reaches the query ports, and existing tests build valid distill objects.

**Contract**:
- `list_notes`, `get_note`, and `list_cards_for_note` declare `user_id: Annotated[UserId, Depends(require_sign_in)]` and pass it as `owner`.
- Module-private factories add an `owner_id` defaulting to a fresh `UserId`, overridable by keyword.
- HTTP fixtures that seed notes use the fixture's fixed person.

### Success Criteria:

#### Automated Verification:
- Offline backend suite passes: `cd backend && uv run pytest -m "not postgres"`
- Postgres lane passes: `cd backend && uv run pytest -m postgres`
- Type check passes: `cd backend && uv run basedpyright`

#### Manual Verification:
- Against an emptied dev database, run `cd backend && uv run alembic upgrade head`, then `uv run alembic downgrade -1`, then `uv run alembic upgrade head`. All three succeed, and `distill_cards.owner_id` exists and is `NOT NULL` at the end.

---

## Phase 4: Distill separation

### Overview

Make the notes queries return only the caller's data, and prove the whole capture → distill chain keeps two people apart.

### Changes Required:

#### 1. Query filtering

**File**: the six query adapters from Phase 3 change 3, plus `backend/tests/unit/distill/contracts/test_list_notes_query_contract.py`, `test_get_note_query_contract.py`, `test_list_cards_for_note_query_contract.py`

**Intent**: Another person's notes and cards are invisible to the caller: absent from lists and not found by id.

**Contract**:
- `list_notes(owner)` returns only notes with `owner_id == owner`. The in-memory adapter filters `list_all()`, and SQL adds the predicate to its `where` clause.
- `get_note(owner, note_id)` and `list_cards_for_note(owner, note_id)` raise `DistillNoteNotFoundError` when the note belongs to another owner.
- Each contract suite gains the matching case on both implementations.

#### 2. Two people across the chain

**File**: `backend/tests/integration/test_capture_distill_separation_http.py`

**Intent**: Request-to-response proof of AC-15 across capture, the outbox, and the background card generation.

**Contract**:
- A module-private fixture composes `InMemoryCaptureComposition` and `InMemoryDistillComposition` on one `InMemoryOutboxStore`, and overrides the notes query providers with in-memory adapters over the distill composition's repositories.
- It uses a switchable `require_sign_in` override.
- Person A drives a session to approval, then the distill worker drains.
- Person B then gets an empty `GET /notes`, and 404 `distill_note_not_found` on `GET /notes/{id}` and `GET /notes/{id}/cards`.
- Person A sees the note with a positive `card_count` and its cards.

### Success Criteria:

#### Automated Verification:
- Distill query contracts pass in memory: `cd backend && uv run pytest tests/unit/distill/contracts -m "not postgres" -v`
- Distill query contracts pass on Postgres: `cd backend && uv run pytest tests/unit/distill/contracts -m postgres -v`
- Chain separation test passes: `cd backend && uv run pytest tests/integration/test_capture_distill_separation_http.py -v`
- Full offline suite passes: `cd backend && uv run pytest -m "not postgres"`
- Postgres lane passes: `cd backend && uv run pytest -m postgres`
- Type check passes: `cd backend && uv run basedpyright`

#### Manual Verification:
- With the backend running on deterministic providers, sign in persons A and B.
- As A, drive a capture session to approval over curl, using the message sequence `test_approve_note_endpoint_returns_topic_and_tags_on_success` uses, and wait for the worker.
- `curl localhost:8000/notes -H "Authorization: Bearer <B>"` returns `[]`.
- `curl -i localhost:8000/notes/<note-id>/cards -H "Authorization: Bearer <B>"` answers 404.
- The same two calls with A's token return the note and its cards.

---

## Testing Strategy

### Unit Tests:

- Phase 2:
  - `nearest` owner filtering in the topic and tag contract suites (in-memory and Postgres)
  - foreign-session not-found in `GenerateReplyCommand` and `ApproveNoteCommand`
- Phase 4: owner filtering and foreign-note not-found in the three distill query contract suites.
- Phases 1 and 3 add no tests. They thread existing tests through the new signatures.

### Integration Tests:

- Phase 2: `test_capture_http.py` gains a two-person session test.
- Phase 4: `test_capture_distill_separation_http.py` proves the chain from approval to cards for two people.
- Postgres contract lanes cover the new columns and predicates.

### Manual Testing Steps:

1. Empty the dev database and run `alembic upgrade head`.
2. Register and sign in two people.
3. Show that B cannot approve A's session.
4. Show that B sees none of A's notes or cards after background generation.

Acceptance scenarios for AC-15 come from `/bdd auth-flow-capture-distill-separation`.

## Performance Considerations

- The owner predicate on `nearest` narrows the pgvector ordering to one person's vocabulary, backed by the `owner_id` indexes on topics and tags.
- The notes list gains an indexed equality predicate on `distill_notes.owner_id`.
- Ownership checks in commands compare values already loaded, with no extra query.
- The gate's token is verified once per request despite being declared on both the router and the route, because FastAPI caches dependencies per request.

## Migration Notes

Two chained, additive revisions add `owner_id UUID NOT NULL` with no default and no backfill (PRD Non-Goals: every instance starts empty).

`alembic upgrade head` fails on a database that already holds capture or distill rows. An operator empties the dev database first, for example with `uv run alembic downgrade base` followed by `uv run alembic upgrade head`.

A pending `note_approved` envelope written before this change lacks `owner_id`. `SaveNoteHandler` logs it as malformed and drops it.

## References

- Effort:
  - `context/efforts/auth-flow/roadmap.md` (S-04)
  - `stories.md` (US-06, AC-15)
  - `prd.md` (FR-008)
  - `frame.md` (FR-05)
- Research: `context/efforts/auth-flow/research-domain-tenancy-and-adapter-grain.md` (problem classes 6 and 7)
- Prior slice: `context/archive/changes/2026-09-14-auth-flow-sign-in-gate/plan.md`
- Rules:
  - `context/foundation/rules/layering.md`
  - `cqrs-lite.md`
  - `exceptions.md`
  - `contract-testing.md`
  - `context/foundation/testing-conventions.md`
