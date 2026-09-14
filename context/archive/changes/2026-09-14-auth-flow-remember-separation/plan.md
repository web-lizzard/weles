# Remember Separation Implementation Plan

## Overview

Make every review sitting belong to the person who opened it, make remember offer, schedule, and source only that person's own cards, and let two people review at the same time without serializing each other. This closes per-person separation across the whole capture → distill → remember chain. Realizes AC-14, AC-16, and AC-17 (`context/efforts/auth-flow/stories.md`, US-06) and the remember half of PRD FR-008 (`context/efforts/auth-flow/roadmap.md`, S-05).

Execution state lives in `todos.md`.

## Current State Analysis

S-04 (`context/archive/changes/2026-09-14-auth-flow-capture-distill-separation/`) left this in place:

- Distill `Note.owner_id` and `Card.owner_id`, persisted as `distill_notes.owner_id` and `distill_cards.owner_id`. The Alembic head is `e63f914a8d6b`.
- Capture and notes routes read `Annotated[UserId, Depends(require_sign_in)]` and pass it inward as `owner`.
- Every HTTP and BDD fixture overrides `require_sign_in` with one `UserId` fixed per fixture (`backend/tests/integration/conftest.py:63-70`, `backend/tests/bdd/conftest.py:52-59`).

Remember still reads and writes across people:

- `ReviewCatalog.list_reviewable` and `get_reviewable` return every live card on the instance (`backend/src/adapters/out/sqlalchemy/remember/review_catalog.py`, `backend/src/adapters/out/in_memory/remember/review_catalog.py`).
- `CardSourceLocator.locate` resolves any card by id.
- `Sitting` has no owner. `SittingReader.latest()` returns the newest sitting on the instance (`backend/src/domain/remember/ports.py:55-61`), and `OpenSittingCommand` and `DueCountQuery` build on it.
- `GradeCardCommand`, `RejectCardCommand`, `RevealBackCommand`, `CurrentCardQuery`, and `CardSourceQuery` load a sitting by id with no ownership check.
- Every remember mutation takes one global exclusion. In Postgres this is `pg_advisory_xact_lock(REMEMBER_LOCK_KEY)` (`backend/src/adapters/out/sqlalchemy/remember/unit_of_work.py:16-41`). In memory it is one `asyncio.Lock` shared by the composition (`backend/tests/integration/support/in_memory_remember.py:77`).
- `remember_sittings` has no owner column.

## Desired End State

- A signed-in person's due count and new sittings draw only on their own live cards.
- Resuming picks the person's own latest sitting, never another person's.
- Another person's sitting answers `404 sitting_not_found` on current card, reveal, source, grade, and rejection. The response is identical to an unknown id, including for an expired foreign sitting.
- Grading and rejecting change only the caller's own scheduling state and cards (AC-16, AC-17).
- Two people can hold remember units of work at the same time. One person's units of work are still serialized.
- `remember_sittings.owner_id UUID NOT NULL` exists, added by one Alembic revision after `e63f914a8d6b`.

Verify with:

- `cd backend && uv run pytest -m "not postgres"`
- `cd backend && uv run pytest -m postgres` (with `TEST_DATABASE_URL`)
- `cd backend && uv run basedpyright`

### Key Discoveries:

- `backend/src/application/remember/commands/open_sitting.py:48` reads the catalog before entering the unit of work. Line 55 reads `uow.sittings.latest()` inside it. The race the lock guards (two opens both minting) is per person once `latest` is per person, which is why a per-person lock is sufficient.
- Scheduling states and review events are keyed by `card_id` and `sitting_id` only. Every read of them starts from card ids produced by the caller's catalog or from a sitting already loaded (`grade_card.py`, `current_card.py`, `due_count.py`). Scoping the catalog and the sitting therefore scopes them, and they get no owner column.
- A sitting's `card_ids` are snapshotted at open from the caller's catalog. `guard_outcome` requires the card to be present in the caller's catalog. `RejectCardCommand` therefore can only emit `card_rejected` for the caller's own card, and `DiscardCardCommand` needs no owner.
- `backend/tests/integration/test_remember_routes.py:23-57` and `backend/tests/bdd/steps/remember_review.py:110,153` seed notes and cards with `owner_id=UserId.new()`, a person different from the fixture's gate.
- `backend/tests/integration/test_capture_distill_separation_http.py` and its `_SwitchableSignInGate` (from `test_capture_http.py`) are the pattern for a two-person chain test.
- `backend/src/adapters/compose.py:185-189`: remember readers, catalog, and locator are process-wide singletons. They stay singletons, because the owner arrives as a call argument.
- `SittingNotFoundError` already maps to 404 (`backend/src/adapters/http/errors.py`). No new exception or mapping is needed.
- The remember contract suites (`backend/tests/unit/remember/contracts/`) are already parametrized `in_memory` and `postgres`. New cases join them.

## What We're NOT Doing

- Owner columns on `remember_review_events`, `remember_scheduling_states`, or `remember_sitting_cards`. They are reachable only through an owned sitting or a card from the caller's catalog.
- An owner on `CardRejectedPayload`, or an ownership check in `DiscardCardCommand`.
- Removing or scoping `distill.NoteRepository.list_all`.
- Replacing the lock with uniqueness constraints or optimistic versioning. Only its grain changes.
- Moving remember queries under the lock (research problem class 2).
- New exception classes or a 403 response. A foreign id is not found.
- Backfilling existing rows (PRD Non-Goals).
- TUI changes. No response shape changes.
- Acceptance scenarios. AC-14, AC-16, and AC-17 scenarios come from `/bdd auth-flow-remember-separation`.
- The uncommitted edit in `backend/src/adapters/compose.py`. It is not part of this change and is never staged by it.

## Implementation Approach

One stubs phase materializes every ownership symbol remember needs: the sitting field, port and command signatures, the unit-of-work factory taking an owner, the ORM column, the Alembic revision, and route parameters. Every exclusion stays unimplemented. Adapters accept the owner and ignore it (`_ = owner`), handlers do not compare it, and the lock stays global. Existing tests are threaded through, and their seeded data is moved onto the gate's person.

Three behavior phases then add exclusions behind tests written first. Each is sized to the per-phase test budget:

1. Read scoping at the ports (catalog, locator, latest).
2. Ownership of a sitting in handlers, proven end to end across the chain.
3. The per-person lock grain.

Enforcement follows S-04's choice:

- A handler that loads a sitting by id compares `sitting.owner_id` with the caller and raises the existing not-found error.
- Collective reads (`list_reviewable`, `latest`) and lookups by card id (`get_reviewable`, `locate`) take the owner and filter at the source.

## Critical Implementation Details

Phase 1 must move every seeded note and card in remember HTTP and BDD fixtures onto the fixture gate's `UserId`. Otherwise Phase 2's catalog filter turns every review test red for a reason unrelated to its subject.

The foreign-owner check in every sitting-loading handler runs immediately after the sitting is loaded, before `is_offered`, `contains`, and `guard_outcome`. Otherwise another person's expired sitting answers `409 sitting_expired` and confirms that it exists.

Postgres `pg_advisory_xact_lock` has a single-bigint form and a two-int4 form, and the two key spaces do not overlap. The per-person lock uses the two-int4 form with a fixed remember namespace and `hashtext(owner)`. A hash collision between two people only serializes them, and never exposes data.

## Phase 1: Remember ownership symbols

### Overview

Put the owner on the sitting, the remember ports, the unit-of-work factory, every remember handler, the table, and the routes. Nothing is excluded yet.

### Changes Required:

#### 1. Remember domain and ports

**File**: `backend/src/domain/remember/sitting.py`, `backend/src/domain/remember/ports.py`

**Intent**: A sitting knows whose it is, and the ports that select cards or sittings accept the person they will later filter by.

**Contract**:
- `Sitting.owner_id: UserId` and `Sitting.open(owner, card_ids, opened_at, showing_limit, resume_horizon=None)`.
- `ReviewCatalog.list_reviewable(owner: UserId)` and `ReviewCatalog.get_reviewable(owner: UserId, card_id)`.
- `CardSourceLocator.locate(owner: UserId, card_id)`.
- `SittingReader.latest(owner: UserId)`. Its docstring becomes "the caller's sitting with the greatest opened_at".

#### 2. Remember application signatures

**File**: `backend/src/application/remember/commands/open_sitting.py`, `backend/src/application/remember/commands/grade_card.py`, `backend/src/application/remember/commands/reject_card.py`, `backend/src/application/remember/commands/reveal_back.py`, `backend/src/application/remember/queries/current_card.py`, `backend/src/application/remember/queries/due_count.py`, `backend/src/application/remember/queries/card_source.py`

**Intent**: The person arrives as an explicit input to every remember handler and to the unit of work, the grain the lock will later key on.

**Contract**:
- Every command takes `uow_factory: Callable[[UserId], UnitOfWork]` and enters `self._uow_factory(owner)`.
- `OpenSittingCommand.handle(owner)` opens with `Sitting.open(owner, …)` and passes `owner` to `list_reviewable` and `latest`.
- `GradeCardCommand.handle(owner, sitting_id, card_id, grade)`, `RejectCardCommand.handle(owner, sitting_id, card_id)`, and `RevealBackCommand.handle(owner, sitting_id, card_id)`.
- `CurrentCardQuery.handle(owner, sitting_id)`, `DueCountQuery.handle(owner)`, and `CardSourceQuery.handle(owner, sitting_id, card_id)`.
- Each passes `owner` to the catalog, locator, or `latest` calls it makes. None compares `sitting.owner_id` yet.

#### 3. Remember adapters and persistence

**File**: `backend/src/adapters/out/in_memory/remember/review_catalog.py`, `backend/src/adapters/out/in_memory/remember/card_source_locator.py`, `backend/src/adapters/out/in_memory/remember/sitting_repository.py`, `backend/src/adapters/out/in_memory/remember/unit_of_work.py`, `backend/src/adapters/out/sqlalchemy/remember/review_catalog.py`, `backend/src/adapters/out/sqlalchemy/remember/card_source_locator.py`, `backend/src/adapters/out/sqlalchemy/remember/sitting_repository.py`, `backend/src/adapters/out/sqlalchemy/remember/query.py`, `backend/src/adapters/out/sqlalchemy/remember/unit_of_work.py`, `backend/src/adapters/out/sqlalchemy/remember/models.py`, `backend/src/adapters/out/sqlalchemy/remember/mapping.py`, `backend/src/adapters/out/sqlalchemy/migrations/versions/<rev>_add_owner_to_remember_sittings.py`, `backend/src/adapters/compose.py`

**Intent**: The owner survives a round trip through both adapters, and every adapter takes the new signatures. The table shape is final in this phase.

**Contract**:
- Catalog, locator, and `latest` implementations accept `owner` and ignore it (`_ = owner`).
- `InMemoryUnitOfWork` and `SqlAlchemyRememberUnitOfWork` accept the owner at construction and still take the global lock.
- `RememberSittingRow.owner_id` (UUID, not null) with a composite index on `(owner_id, opened_at)`. The mappers carry it both ways, and `save` writes it on insert and never updates it.
- Migration: `down_revision = "e63f914a8d6b"`. It adds the column `NOT NULL` with no server default, plus the index with an `op.f` name. `downgrade` drops both.
- `compose.py`'s `_remember_unit_of_work(owner)` passes the owner. Only the remember wiring hunks are staged, never the unrelated uncommitted LLM-provider hunk.

#### 4. Remember routes and test fixtures

**File**: `backend/src/adapters/http/remember.py`, `backend/tests/integration/support/in_memory_remember.py`, `backend/tests/integration/conftest.py`, `backend/tests/integration/test_remember_routes.py`, `backend/tests/bdd/steps/remember_review.py`, remember unit, contract, property, and Postgres test modules that call the changed signatures

**Intent**: The gate's `UserId` reaches every remember handler. Test clients review cards that belong to the person they act as, and the in-memory composition can share distill's repositories.

**Contract**:
- All seven remember routes declare `user_id: Annotated[UserId, Depends(require_sign_in)]` and pass it as `owner`.
- `InMemoryRememberComposition.create` gains optional `notes`, `cards`, and `outbox_store` arguments, used in place of fresh ones when given. `unit_of_work(owner)` accepts the owner.
- `RememberTestContext` exposes the fixture gate's `user_id`. Route tests and BDD remember steps seed notes and cards with that person.
- Existing call sites are threaded with an owner and assert nothing new.

### Success Criteria:

#### Automated Verification:
- Offline backend suite passes: `cd backend && uv run pytest -m "not postgres"`
- Postgres lane passes: `cd backend && uv run pytest -m postgres`
- Type check passes: `cd backend && uv run basedpyright`

#### Manual Verification:
- Against an emptied dev database, run `cd backend && uv run alembic upgrade head`, then `uv run alembic downgrade -1`, then `uv run alembic upgrade head`. All three succeed, and `remember_sittings.owner_id` exists and is `NOT NULL` at the end.

---

## Phase 2: Remember read scoping

### Overview

Make the catalog, the source locator, and the latest-sitting lookup see only the caller's data.

### Changes Required:

#### 1. Catalog and locator per person

**File**: `backend/src/adapters/out/in_memory/remember/review_catalog.py`, `backend/src/adapters/out/sqlalchemy/remember/review_catalog.py`, `backend/src/adapters/out/in_memory/remember/card_source_locator.py`, `backend/src/adapters/out/sqlalchemy/remember/card_source_locator.py`, `backend/tests/unit/remember/contracts/test_review_catalog_contract.py`, `backend/tests/unit/remember/contracts/test_card_source_locator_contract.py`

**Intent**: Another person's card is never offered for review and never resolves to a source.

**Contract**:
- `list_reviewable(owner)` returns only live cards with `owner_id == owner`. `get_reviewable(owner, card_id)` and `locate(owner, card_id)` return `None` for another person's card.
- SQL adds `DistillCardRow.owner_id == owner.value` to each `where` clause. In memory, the adapters compare `card.owner_id`.
- Contract cases, on both implementations:
  - The catalog list omits another owner's live card.
  - `get_reviewable` returns `None` for it.
  - `locate` returns `None` for it.

#### 2. Latest sitting per person

**File**: `backend/src/adapters/out/in_memory/remember/sitting_repository.py`, `backend/src/adapters/out/sqlalchemy/remember/sitting_repository.py`, `backend/tests/unit/remember/contracts/test_sitting_repository_contract.py`

**Intent**: Resume and due counting never pick up another person's sitting.

**Contract**:
- `latest(owner)` returns the greatest `opened_at` among sittings with `owner_id == owner`, or `None`.
- The contract case covers another owner's newer sitting: it is ignored, and `latest` returns the caller's own sitting, or `None` when the caller has none.

### Success Criteria:

#### Automated Verification:
- Remember contracts pass in memory: `cd backend && uv run pytest tests/unit/remember/contracts -m "not postgres" -v`
- Remember contracts pass on Postgres: `cd backend && uv run pytest tests/unit/remember/contracts -m postgres -v`
- Full offline suite passes: `cd backend && uv run pytest -m "not postgres"`
- Type check passes: `cd backend && uv run basedpyright`

#### Manual Verification:
- With the backend running on deterministic providers, sign in persons A and B through `POST /auth/register` and `POST /auth/sign-in`.
- As A, drive a capture session to approval over curl, as in S-04's Phase 4 recipe, and wait for the worker.
- `curl localhost:8000/due-cards/count -H "Authorization: Bearer <B>"` reports nothing due.
- `curl -X POST localhost:8000/review-sittings -H "Authorization: Bearer <B>"` answers `nothing_due`.
- The same two calls with A's token report A's due cards and open a sitting.

---

## Phase 3: Sitting ownership and chain separation

### Overview

Make every handler that takes a sitting id refuse another person's sitting. Then prove over HTTP that no read or change crosses between two people anywhere in the chain.

### Changes Required:

#### 1. Sitting ownership in handlers

**File**: `backend/src/application/remember/commands/grade_card.py`, `backend/src/application/remember/commands/reject_card.py`, `backend/src/application/remember/commands/reveal_back.py`, `backend/src/application/remember/queries/current_card.py`, `backend/src/application/remember/queries/card_source.py`, `backend/tests/unit/remember/test_grade_card_command.py`, `backend/tests/unit/remember/test_reject_card_command.py`, `backend/tests/unit/remember/test_reveal_back_command.py`, `backend/tests/unit/remember/test_current_card_query.py`, `backend/tests/unit/remember/test_card_source_query.py`

**Intent**: Another person's sitting is indistinguishable from a sitting that does not exist, and nothing is written for it.

**Contract**:
- Each handler raises `SittingNotFoundError` when the sitting is missing or `sitting.owner_id != owner`, before `is_offered`, `contains`, or `guard_outcome`.
- Each module gains one case: a sitting opened by another owner raises `SittingNotFoundError`. For the three commands, the case also shows that no review event is stored.

#### 2. Two people across the chain

**File**: `backend/tests/integration/test_remember_separation_http.py`

**Intent**: Request-to-response proof of AC-14, AC-16, and AC-17 across capture, distill's background card generation, and remember.

**Contract**:
- A module-private fixture composes `InMemoryCaptureComposition`, `InMemoryDistillComposition`, and `InMemoryRememberComposition` over one `InMemoryOutboxStore` and distill's note and card repositories. It uses `_SwitchableSignInGate`.
- Person A drives a session to approval, the distill worker drains, and A opens a sitting.
- Person B then gets:
  - nothing due from `GET /due-cards/count`;
  - `nothing_due` from `POST /review-sittings`;
  - `404 sitting_not_found` on A's sitting for current card, back, source, grade, and rejection.
- Person A then grades the card in front successfully, showing B's attempts changed nothing.

### Success Criteria:

#### Automated Verification:
- Remember handler tests pass: `cd backend && uv run pytest tests/unit/remember -m "not postgres" -v`
- Chain separation test passes: `cd backend && uv run pytest tests/integration/test_remember_separation_http.py -v`
- Full offline suite passes: `cd backend && uv run pytest -m "not postgres"`
- Postgres lane passes: `cd backend && uv run pytest -m postgres`
- Type check passes: `cd backend && uv run basedpyright`

#### Manual Verification:
- With the backend running on deterministic providers, as person A open a sitting with `curl -X POST localhost:8000/review-sittings -H "Authorization: Bearer <A>"` and note `sitting_id` and `card_id`.
- `curl -i localhost:8000/review-sittings/<sitting_id>/current-card -H "Authorization: Bearer <B>"` answers 404 `sitting_not_found`.
- `curl -i -X POST localhost:8000/review-sittings/<sitting_id>/cards/<card_id>/grade -H "Authorization: Bearer <B>" -H "Content-Type: application/json" -d '{"grade":"good"}'` answers 404 `sitting_not_found`.
- The same current-card call with A's token still returns the same card.

---

## Phase 4: Per-person remember lock

### Overview

Re-key remember's mutation exclusion from the whole instance to one person.

### Changes Required:

#### 1. In-memory lock per person

**File**: `backend/src/adapters/out/in_memory/remember/unit_of_work.py`, `backend/tests/integration/support/in_memory_remember.py`, `backend/tests/unit/remember/test_unit_of_work.py`

**Intent**: One person's review never waits on another person's, while two windows for the same person stay serialized.

**Contract**:
- The in-memory unit of work takes its lock from a per-owner registry (`asyncio.Lock` per `UserId`, created on first use) instead of one shared lock. The composition holds the registry.
- Unit cases:
  - The existing same-owner ordering test still holds.
  - A second owner's window enters while the first owner's window is still open.

#### 2. Postgres advisory lock per person

**File**: `backend/src/adapters/out/sqlalchemy/remember/unit_of_work.py`, `backend/tests/integration/postgres/test_remember_persistence.py`

**Intent**: The same grain in Postgres.

**Contract**:
- `__aenter__` executes `SELECT pg_advisory_xact_lock(:namespace, hashtext(:owner))`, with a module constant int4 namespace replacing `REMEMBER_LOCK_KEY`.
- Postgres case: while one owner's unit of work is held open, another owner's unit of work enters and commits.

### Success Criteria:

#### Automated Verification:
- Unit-of-work tests pass: `cd backend && uv run pytest tests/unit/remember/test_unit_of_work.py -v`
- Postgres remember persistence passes: `cd backend && uv run pytest tests/integration/postgres/test_remember_persistence.py -m postgres -v`
- Full offline suite passes: `cd backend && uv run pytest -m "not postgres"`
- Postgres lane passes: `cd backend && uv run pytest -m postgres`
- Type check passes: `cd backend && uv run basedpyright`

---

## Testing Strategy

### Unit Tests:

- Phase 2: owner filtering in the review catalog, card source locator, and sitting repository contract suites (in memory and Postgres).
- Phase 3: foreign sitting is not found, with no write, in the three remember commands and two sitting queries.
- Phase 4: per-owner lock ordering on the in-memory unit of work.
- Phase 1 adds no tests. It threads existing tests through the new signatures.

### Integration Tests:

- Phase 3: `test_remember_separation_http.py` proves the chain from capture approval to review for two people.
- Phase 4: one Postgres case shows two owners' remember units of work do not block each other.
- The Postgres contract lanes cover the new column and predicates.

### Manual Testing Steps:

1. Empty the dev database and run `alembic upgrade head`.
2. Register and sign in two people. Person A captures and approves a note.
3. Show that B has nothing due and cannot open a sitting over A's cards.
4. Show that B gets 404 on A's sitting while A keeps reviewing.

Acceptance scenarios for AC-14, AC-16, and AC-17 come from `/bdd auth-flow-remember-separation`.

## Performance Considerations

- Catalog queries gain an equality predicate on `distill_cards.owner_id`, which is not indexed today. At a two-person scale the sequential filter is negligible, so no index is added by this change.
- `latest(owner)` is served by the composite `(owner_id, opened_at)` index.
- Ownership checks in handlers compare values already loaded, with no extra query.
- The per-person lock removes cross-person serialization of remember commands.

## Migration Notes

One additive revision adds `remember_sittings.owner_id UUID NOT NULL` with no default and no backfill (PRD Non-Goals: every instance starts empty).

`alembic upgrade head` fails on a database that already holds sittings. An operator empties the dev database first, for example with `uv run alembic downgrade base` followed by `uv run alembic upgrade head`.

## References

- Effort:
  - `context/efforts/auth-flow/roadmap.md` (S-05)
  - `stories.md` (US-06, AC-14, AC-16, AC-17)
  - `prd.md` (FR-008)
  - `frame.md` (FR-05)
- Research: `context/efforts/auth-flow/research-domain-tenancy-and-adapter-grain.md` (problem classes 1, 3, 5, and 6)
- Prior slice: `context/archive/changes/2026-09-14-auth-flow-capture-distill-separation/plan.md`
- Rules:
  - `context/foundation/rules/layering.md`
  - `cqrs-lite.md`
  - `exceptions.md`
  - `contract-testing.md`
  - `context/foundation/testing-conventions.md`
