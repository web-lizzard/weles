# Review Sitting Core Implementation Plan

> Revision 1 (2026-09-10): the five unstarted adapter and delivery phases are split into stubs-then-behavior pairs, because the closed contract session shaped only domain and application — every adapter symbol was still absent when its `#### Tests` row fired, so the generated tests failed on collection rather than on assertions. The acceptance-migration phase additionally absorbs the handler unit tests. Phases 1–7 and the whole domain and application design survive untouched. Prior version: plan-versions/v1-plan.md

## Overview

Deliver the first review sitting end to end: opening a session over everything due,
presenting one card at a time, revealing a back on request, taking a four-step grade,
and moving that card's schedule on. The domain shape is already on disk as signatures
without bodies — this plan fills those bodies, adds the five adapters behind them,
exposes the flow over HTTP, and grows the acceptance layer to cover the behaviours
`frame.md` states beyond the nine acceptance criteria.

Execution state for this plan lives in `todos.md`, sibling of this file.

## Current State Analysis

A closed `/discover-contracts` session (`discover-contracts.md`, `status: closed`) put the
whole remember architecture into the working tree as signatures with `...` bodies:

- `backend/src/domain/remember/` — `sitting.py`, `sitting_completion.py`, `sitting_order.py`,
  `review_event.py`, `scheduling_state.py`, `value_objects.py`, `ports.py`, `exceptions.py`
- `backend/src/application/remember/` — `ports.py` (`Clock`, `UnitOfWork`), `dto.py`,
  `commands/open_sitting.py`, `commands/grade_card.py`, `queries/current_card.py`,
  `queries/reveal_back.py`

Nothing else exists. There is no `adapters/out/in_memory/remember/`, no HTTP router, no
compose wiring, and `fsrs` is not a backend dependency.

The acceptance layer is already red: four feature files under
`backend/tests/features/remember-flow/` cover AC-01 through AC-09, and
`backend/tests/bdd/steps/remember_review.py` drives them through module-private
`_InMemory*` repositories and a `_FakeScheduler` — doubles that exist only because the
real adapters do not.

Constraints in force: hexagonal layering and `InMemoryFirst`
(`context/foundation/rules/layering.md`), one behavioural contract suite per port
(`context/foundation/rules/contract-testing.md`), CQRS-lite with `UnitOfWork` owned by
commands only (`context/foundation/rules/cqrs-lite.md`), and the shared `CoreException`
root with its exhaustiveness test (`context/foundation/rules/exceptions.md`) — every
remember exception code is already mapped in `backend/src/adapters/http/errors.py`.

## Desired End State

A user can call the review API, work through every due card, reveal each back, grade it
one of four ways, and see the card's next-due date move — with every grade permanent the
moment it is taken, and an unfinished sitting costing nothing. Verified by: the full
backend suite green (`cd backend && uv run pytest`), including the remember acceptance
scenarios, the three remember port contract suites, and the `fsrs` adapter's
repeatability test.

### Key Discoveries:

- `backend/src/domain/remember/scheduling_state.py:19` — `card_is_due(state, as_of)` takes no
  stamp, but "a stale stamp makes a card due" needs one. This signature changes.
- `backend/src/domain/distill/ports.py:16` — distill's `CardRepository` exposes only
  `list_by_note`. The catalog adapter walks `NoteRepository.list_all()` instead, exactly as
  `backend/src/adapters/out/in_memory/distill/list_cards_for_note_query.py:22` already does,
  and filters `card.discard is None`. No distill port changes.
- `backend/src/adapters/out/in_memory/distill/unit_of_work.py:32` — the in-memory UoW pattern
  is snapshot on `__aenter__`, restore on `__aexit__` unless `commit()` ran. Remember's UoW
  mirrors it over three repositories.
- `backend/tests/unit/distill/contracts/test_card_repository_contract.py:20` — contract suites
  are `_IMPLEMENTATIONS: list[Callable[[], Port]]` parametrized with `ids=["in_memory"]`.
- `backend/src/adapters/http/errors.py:40-47` — all seven remember exception codes are already
  in `EXCEPTION_STATUS_MAP`; `backend/tests/unit/test_http_error_mapping.py` walks the
  `CoreException` tree and would fail on any gap.
- `backend/src/config/settings.py:31` — `sitting_max_showings: int = 2` already exists.
- `context/efforts/remember-flow/research.md:56` — FSRS fuzz fires only when the post-review
  state is `Review` and the interval is ≥ 2.5 days, drawing from module-level `random()`.
- `backend/tests/bdd/test_features.py` — `bdd.steps.remember_review` is already registered in
  `pytest_plugins`; new scenarios need no loader change, and reusing existing AC tags needs no
  new marker in `[tool.pytest.ini_options]`.

## What We're NOT Doing

- AC-10 through AC-22: resume, expiry, due count, capture prompt, rejection, source jump,
  capture entry. Each belongs to a later slice on the `remember-flow` roadmap.
- Expiry of a sitting and offering an unfinished one back — S-02.
- Topic- or note-scoped selection, batch-of-N and timebox session modes.
- Any substitutable policy for selection or completion, and any field on the sitting
  recording which policy it began under.
- A SQL or Notion adapter for any of the five seams. In-memory only, per `InMemoryFirst`.
- A database lock (`SELECT … FOR UPDATE` or equivalent) for concurrent grades. Phase 9's
  in-memory UoW holds an `asyncio.Lock`; SQL takes the same exclusion when that adapter exists.
- `fsrs[optimizer]`, `Scheduler.to_dict()` persistence, and the library's own `ReviewLog`.
- Any TUI surface.

## Implementation Approach

Inside out, in the order the dependencies actually run: domain rules first (they need
nothing), then the application flows that compose them, then the adapters that satisfy
their ports, then HTTP. The acceptance layer is grown first, at the very top of the plan,
so the frame-derived behaviours are red before any body is written — and the step
definitions are migrated onto the real adapters last, once those adapters exist.

The domain and application phases fill bodies into signatures a closed `/discover-contracts`
session already put on disk, so each is a single phase carrying its own `#### Tests` row. That
session never reached the adapters or the HTTP surface: every symbol there is still absent, so
those five units are each planned as a stubs phase followed by a behaviour phase. The stubs
phase materializes modules, classes, and method signatures with `...` bodies and carries no
`#### Tests` row; the behaviour phase that follows fills them against tests that import real
names rather than failing on collection.

Two decisions from the planning interview change what is on disk:

- `card_is_due` grows a `current_stamp: SchedulerStamp` parameter. A memoized record whose
  stamp does not match the live scheduler is treated exactly like no record at all: the card
  is due, and `GradeCardCommand` rebuilds it from the log when the card is graded. Nothing
  reconstructs on the open path.
- `Sitting.next_card` / `is_finished` / `_eligible_pool` drop events whose `sitting_id` is not
  their own, so completeness and ordering cannot be corrupted by a caller passing
  `list_by_card` output.

## Critical Implementation Details

`fsrs` applies interval fuzz by calling module-level `random()`, so the only way to make
replay reproduce a `due_at` bit-for-bit is to seed the global generator from the event's own
recorded facts around the call: `state = random.getstate()`, `random.seed(hash of card_id +
reviewed_at + grade)`, `scheduler.review_card(...)`, `random.setstate(state)`. That region is
synchronous and holds no `await`, so it is atomic with respect to the event loop and needs no
lock — an assumption that holds only while the scheduler is called from the loop thread, and
which the adapter must state in a comment. If the port is ever driven from a threadpool, a
`threading.Lock` is the only thing that helps; an `asyncio.Lock` cannot guard a region no
coroutine can interleave with.

That FSRS-region lock is not the grade race. `GradeCardCommand` decides presentability from
the sitting's event log, so a second grade of the same showing is refused only after the
first commit is visible. Two overlapping `handle` calls on the same in-front card both pass
`card_id == next_card` and both append events unless the whole read-then-write window is
serialized. `SchedulerStamp` does not close this — it marks memoized scheduler state stale
after an algorithm or parameter bump. Phase 9's in-memory unit of work takes a shared
`asyncio.Lock` on `__aenter__` and releases it on `__aexit__` (commit or rollback), covering
open and grade because both already own that UoW window. The lock is constructed once at
composition and passed into every UoW instance — a per-instance lock would not exclude a
second factory call. Per-sitting locking is the wrong grain here: `OpenSittingCommand`
enters the UoW before a sitting id exists. A later SQL adapter maps the same window to a
transaction lock (`SELECT … FOR UPDATE` on the sitting, or equivalent), not an `asyncio.Lock`.

## Phase 1: Extend the acceptance layer to the frame's behaviours

### Overview

Grow the remember-flow feature files with the behaviours `frame.md` states beyond the bare
acceptance criteria, tagged under the AC each deepens so the traceability chain to
`stories.md` stays intact. This phase authors tests only; it is `/bdd`'s work, not
`/implement`'s, and closes red.

### Changes Required:

#### 1. Feature files

**File**: `backend/tests/features/remember-flow/US-01-everything-due-in-one-command.feature`

**Intent**: Cover the frame's membership rules that AC-01 implies but does not state.

**Contract**: Adds scenarios under `@remember-flow @AC-01` — a card discarded elsewhere while
the sitting runs drops out of it when the set is read rather than being removed from it; a
card whose memoized stamp does not match the live scheduler is treated as due.

**File**: `backend/tests/features/remember-flow/US-02-answer-before-you-are-shown-it.feature`

**Intent**: Cover presentation stability and the losslessness of walking away.

**Contract**: Adds scenarios under `@remember-flow @AC-04` — the same card stays in front
across separate requests against the same sitting id; the card just graded is never the next
card shown while another undone card exists. Under `@remember-flow @AC-05` — grades already
given survive abandoning the sitting, and the cards not reached are still due next time.

**File**: `backend/tests/features/remember-flow/US-04-the-one-you-missed-comes-back.feature`

**Intent**: Cover the completion rule's second half and `Hard`'s parity with the lowest grade.

**Contract**: Adds scenarios under `@remember-flow @AC-09` — a card graded `hard` returns
within the same sitting as surely as `forgot` does; a card shown the configured number of
times counts as finished even without a `Good` grade; completion is derived from that
sitting's grades and never from a card's next-due date.

#### 2. Step definitions

**File**: `backend/tests/bdd/steps/remember_review.py`

**Intent**: Add the steps those scenarios need, appending to the existing module.

**Contract**: New `@given` / `@when` / `@then` functions only. The existing fixture and
doubles stay as they are — Phase 16 replaces them once the real adapters exist. No new
pytest marker: every tag reuses an `AC-nn` already registered in `pyproject.toml`.

### Success Criteria:

#### Manual Verification:
- Run `/bdd remember-flow-review-session` and confirm each new scenario carries a tag that
  already exists in `[tool.pytest.ini_options] markers`.
- `cd backend && uv run pytest tests/bdd -m "remember-flow" -v` collects every new scenario
  with no undefined step, and fails on assertions rather than on collection.

This phase has no Automated Verification subsection on purpose: authoring these scenarios is
`/bdd`'s work, and the pass that authors a test never also satisfies it.

---

## Phase 2: Domain — membership and due-ness

### Overview

Fill the rules that need no review log: what a valid sitting is, what membership means when
a card has been discarded elsewhere, and when a card counts as due.

### Changes Required:

#### 1. Value objects

**File**: `backend/src/domain/remember/value_objects.py`

**Intent**: Make `ShowingLimit` refuse a value that cannot keep the frame's promise that a
failed card returns at least once.

**Contract**: `ShowingLimit._validate_positive` raises `InvalidShowingLimitError` when
`value < 1`; returns `self` otherwise.

#### 2. Sitting membership

**File**: `backend/src/domain/remember/sitting.py`

**Intent**: A sitting is meaningless with no cards, and its stored set is a record, not a
mutable collection.

**Contract**: `_validate_intent` raises `EmptySittingError` on an empty `card_ids`.
`contains(card_id)` tests the stored set. `visible(live)` returns
`self.card_ids & live` — the stored set is never rewritten.

#### 3. Due-ness

**File**: `backend/src/domain/remember/scheduling_state.py`

**Intent**: A card is due when nothing reliable says otherwise, and a memoized record
produced by a different scheduler is not reliable.

**Contract**: `card_is_due(state: SchedulingState | None, as_of: datetime, current_stamp:
SchedulerStamp) -> bool` — `True` when `state is None`, when `state.stamp != current_stamp`,
or when `state.due_at <= as_of`. The `<=` includes a card due at exactly this instant.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -v`
- `cd backend && uv run basedpyright src`

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/remember/test_scheduling_state.py -v` and confirm
  the stale-stamp case is asserted separately from the missing-record case.

---

## Phase 3: Domain — completion and ordering

### Overview

Fill the two named rules the frame demands exist once each: what finishes a card in this
sitting, and which card comes next.

**Implementation note**: the contract sketch below names `SittingCompletion` and
`sitting_seeded_draw` as separate modules. They ship as private methods on `Sitting`
(`_card_is_finished`, `_showing_count`, `_seeded_pick`, `_draw_seed`) so completion and
ordering cannot be reached outside the aggregate. Behaviour and tests are unchanged; only
the encapsulation boundary moved.

### Changes Required:

#### 1. Completion

**File**: `backend/src/domain/remember/sitting_completion.py`

**Intent**: Completion is read off this sitting's grades and never off a next-due date.

**Contract**: `__init__` stores events and limit. `showing_count(card_id)` counts that card's
events. `grade_finishes_card(grade)` is membership in `FINISHING_GRADES`.
`card_is_finished(card_id)` is a finishing grade in this sitting, or
`showing_count >= limit.value`. `sitting_is_finished(membership, present)` is `True` when
every id in `present` is finished — discarded members are not waited on.

#### 2. Ordering

**File**: `backend/src/domain/remember/sitting.py`

**Intent**: The presented card is drawn from the undone cards shown fewest times, and no
caller can bypass that by handing in the wrong events.

**Contract**: `_eligible_pool(present, events)` filters events to `sitting_id == self.id`,
drops finished cards, and keeps only those at the minimum showing count — so no card is
presented while another undone member has a strictly lower count. `next_card` returns
`sitting_seeded_draw(self.id, events).pick(sorted(pool))` or `None` on an empty pool.
`is_finished` delegates to `SittingCompletion.sitting_is_finished`. Both apply the same
foreign-event filter.

#### 3. The draw

**File**: `backend/src/domain/remember/sitting_order.py`

**Intent**: The ordering rule is fixed; only its random source is injectable.

**Contract**: `sitting_seeded_draw(sitting_id, events)` returns a `Draw` whose `pick` is a
pure function of the sitting id and the events — same inputs, same pick, no stored cursor.
Seed derives from `sitting_id.value` and the count and identity of the events, never from
wall-clock or process state.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -v`
- `cd backend && uv run ruff check src tests`

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/remember/test_sitting.py -v` twice in a row and
  confirm the seeded-draw assertions pick the same card both runs.

### Review r1

Artifact: `reviews/2026-09-10-r1-property-test-phases-2-3-4-.md`

- `R1-F1` — Foreign sitting events change the drawn next card
  Fix: The shrunk two-card example with sitting `5ab7c383-a883-4fdf-ab28-0d827faaea53` must fail the pin until `_draw_seed` / `_seeded_pick` use only this sitting's events, then remain as regression.

### Review r2

Artifact: `reviews/2026-09-10-r2-mutation-test-phases-2-3-4-.md`

- `R2-F1` — Eligible pool must exclude members above the minimum showing count
  Fix: When one member has been shown more than another unfinished member, `next_card` must draw only from those at the minimum showing count.
- `R2-F2` — Draw seed must incorporate the sitting id
  Fix: Two sittings with identical card sets and event sequences must not be assumed to draw the same card unless their sitting ids match.
- `R2-F3` — Draw seed must sort events before hashing
  Fix: Appending a later `reviewed_at` event must change the draw when multiple unfinished cards tie on showing count.
- `R2-F4` — Draw seed must incorporate each event's card id
  Fix: Each sitting event's own `card_id` must contribute to the draw seed so reviews on different cards diverge.
- `R2-F5` — Draw seed must use eight big-endian digest bytes
  Fix: The seeded draw must derive from exactly the first eight big-endian bytes of the SHA-256 digest over the joined parts.

---

## Phase 4: Domain — reconstruction from the log

### Overview

Make a card's scheduling state fully rebuildable from its review events alone, which is what
lets the memoized record be discarded at any moment.

### Changes Required:

#### 1. Replay

**File**: `backend/src/domain/remember/ports.py`

**Intent**: Replaying a card's events in order reproduces the same state the live path
produced, without any reader needing the sitting.

**Contract**: `SchedulingReplay.replay(card_id, events)` folds `Scheduler.review` over the
events in `reviewed_at` order, threading each result in as the next `previous`, and returns
`None` for an empty sequence. Only `card_id`, `reviewed_at` and `grade` are read — the
scheduler never sees `sitting_id`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -v`

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/remember/test_scheduling_replay.py -v` and confirm
  a replay of N events equals the state built by N sequential live reviews.

---

## Phase 5: Application — opening a sitting

### Overview

Turn "everything due right now" into a persisted sitting with its first card in front, or
into a straight answer that nothing is waiting.

### Changes Required:

#### 1. Open command

**File**: `backend/src/application/remember/commands/open_sitting.py`

**Intent**: One gesture opens a review over the whole due set; an empty day creates no
session at all.

**Contract**: `handle()` follows the documented eight steps — `clock.now()` once,
`catalog.list_reviewable()`, `get_many` for memoized states, `card_is_due(state, as_of,
scheduler.stamp())` for the due set, `NothingDueDTO` and no write when it is empty, otherwise
`Sitting.open(due, as_of, self._showing_limit)` saved and committed in one UoW, then the
first front via `next_card(present, events=[])`. The command gains a `scheduler: Scheduler`
constructor dependency so it can ask for the live stamp.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -v`
- `cd backend && uv run basedpyright src`

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/remember/test_open_sitting_command.py -v` and
  confirm the nothing-due case asserts on the repository being untouched, not only on the DTO.

---

## Phase 6: Application — revealing a back and rereading the current card

### Overview

Fill the two read paths: the back on request, and the card in front for a later request that
carries only a sitting id.

### Changes Required:

#### 1. Reveal

**File**: `backend/src/application/remember/queries/reveal_back.py`

**Intent**: A back is reachable only by asking, and asking never writes.

**Contract**: `handle(sitting_id, card_id)` raises `SittingNotFoundError`,
`CardNotInSittingError`, or `CardNotReviewableError`, and otherwise returns front and back.
It does not re-derive the card in front.

#### 2. Current card

**File**: `backend/src/application/remember/queries/current_card.py`

**Intent**: A sitting spans many requests, so the card in front must survive a reread.

**Contract**: `handle(sitting_id)` loads the sitting and its events, intersects membership
with the catalog through `visible`, and returns `sitting.next_card(...)` as a
`PresentedCardDTO` with `sitting_complete` from `is_finished`. No `UnitOfWork`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -v`

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/remember/test_current_card_query.py -v` and confirm
  two consecutive handles over the same sitting return the same `card_id`.

---

## Phase 7: Application — grading a card

### Overview

The write path: guard that this card is really the one in front, record the event, move the
card's schedule, and hand back the next front or completion.

### Changes Required:

#### 1. Grade command

**File**: `backend/src/application/remember/commands/grade_card.py`

**Intent**: A grade is permanent the moment it is taken, and of event and memoized state the
event is the one that must not be lost.

**Contract**: `handle(sitting_id, card_id, grade)` follows the documented nine steps.
Guard order is `SittingNotFoundError`, `CardNotInSittingError`, `SittingAlreadyCompleteError`,
then `CardNotPresentableError` when `card_id != sitting.next_card(...)`. `reviewed_at =
clock.now()` is captured once and used for both the event and the scheduler.
`previous` is the memoized state when its stamp matches `scheduler.stamp()`, otherwise
`SchedulingReplay.replay` over the card's prior events. One UoW saves the event first, then
the scheduling state, then commits. The DTO carries the recomputed next front, or completion.
The sitting-log guards are sequential, not a concurrency control. Phase 9 serializes the
UoW window with a shared `asyncio.Lock`; this command does not take a lock of its own.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -v`
- `cd backend && uv run pytest tests/bdd -m "remember-flow and AC-09" -v`

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/remember/test_grade_card_command.py -v` and confirm
  the stale-stamp path asserts the replayed state was used, not the memoized one.

---

## Phase 8: In-memory adapter stubs

### Overview

Materialize every symbol the three transactional seams need — modules, classes, and method
signatures with `...` bodies — so the behaviour phase that follows can be driven by tests that
import real names. No logic is written here.

### Changes Required:

#### 1. Package

**File**: `backend/src/adapters/out/in_memory/remember/__init__.py`

**Intent**: The remember adapter package exists alongside `capture/` and `distill/`.

**Contract**: Empty module.

#### 2. Repository stubs

**File**: `backend/src/adapters/out/in_memory/remember/sitting_repository.py`

**Contract**: `class InMemorySittingRepository` with `__init__`, `async def save(self, sitting: Sitting) -> None`,
`async def get(self, sitting_id: SittingId) -> Sitting | None`, `def snapshot(self) -> dict[SittingId, Sitting]`,
`def restore(self, snapshot: dict[SittingId, Sitting]) -> None`. Bodies are `...`.

**File**: `backend/src/adapters/out/in_memory/remember/review_event_store.py`

**Contract**: `class InMemoryReviewEventStore` with `save(event)`, `list_by_card(card_id)`,
`list_by_sitting(sitting_id)`, `snapshot()`, `restore(snapshot)`. Bodies are `...`.

**File**: `backend/src/adapters/out/in_memory/remember/scheduling_state_repository.py`

**Contract**: `class InMemorySchedulingStateRepository` with `save(state)`, `get(card_id)`,
`get_many(card_ids)`, `snapshot()`, `restore(snapshot)`. Bodies are `...`.

#### 3. Unit of work and clock stubs

**File**: `backend/src/adapters/out/in_memory/remember/unit_of_work.py`

**Contract**: `class InMemoryUnitOfWork` taking the three repositories and an `asyncio.Lock`,
with `__aenter__`, `__aexit__`, and `commit()`. Bodies are `...`.

**File**: `backend/src/adapters/out/in_memory/remember/clock.py`

**Contract**: `class SystemClock` with `def now(self) -> datetime`. Body is `...`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src`
- `cd backend && uv run basedpyright src`
- `cd backend && uv run python -c "import adapters.out.in_memory.remember.unit_of_work"`

#### Manual Verification:
- Confirm every method body in the new package is `...` — no logic landed early.

---

## Phase 9: Fill the in-memory adapters, the unit of work, and the port contracts

### Overview

Give the three transactional seams real behaviour and the behavioural contract suite each port
owes, so the flows stop being proven against hand-rolled doubles.

### Changes Required:

#### 1. Repositories

**File**: `backend/src/adapters/out/in_memory/remember/sitting_repository.py`

**Intent**: Round-trip the whole aggregate, `showing_limit` included, so a later env change
cannot retcon an open sitting.

**Contract**: `save(sitting)` stores by id; `get(sitting_id)` returns `None` when absent;
`snapshot()` / `restore()` copy the store shallowly, as the aggregate is frozen.

**File**: `backend/src/adapters/out/in_memory/remember/review_event_store.py`

**Intent**: The log answers by card for replay and by sitting for the sitting's own reads.

**Contract**: `list_by_card(card_id)` and `list_by_sitting(sitting_id)` both return
chronological order by `reviewed_at`.

**File**: `backend/src/adapters/out/in_memory/remember/scheduling_state_repository.py`

**Intent**: Memoized state keyed by card, with the batch read the open path needs.

**Contract**: `get_many(card_ids)` returns only the ids it holds — never a `None` placeholder.

#### 2. Unit of work and clock

**File**: `backend/src/adapters/out/in_memory/remember/unit_of_work.py`

**Intent**: Commands own the commit boundary; nothing survives an exception; overlapping
commands cannot interleave reads and writes on the shared in-memory stores.

**Contract**: Mirrors `adapters/out/in_memory/distill/unit_of_work.py` — snapshots all three
repositories on `__aenter__`, restores them on `__aexit__` unless `commit()` ran. In addition,
composition constructs one `asyncio.Lock` and every UoW instance receives it. `__aenter__`
`await`s that lock before snapshotting; `__aexit__` releases it after restore-or-keep, always.
A second `uow_factory()` call therefore waits until the first window closes, which is what
stops two overlapping `GradeCardCommand.handle` calls from both seeing the same `next_card`.

**File**: `backend/src/adapters/out/in_memory/remember/clock.py`

**Intent**: One named source of timezone-aware UTC.

**Contract**: `SystemClock.now()` returns `datetime.now(UTC)`.

#### 3. Contract suites

**File**: `backend/tests/unit/remember/contracts/test_sitting_repository_contract.py`,
`test_review_event_store_contract.py`, `test_scheduling_state_repository_contract.py`

**Intent**: Every port carries one behavioural suite parametrized over its implementations.

**Contract**: `_IMPLEMENTATIONS: list[Callable[[], Port]]` with `ids=["in_memory"]`, per
`context/foundation/rules/contract-testing.md`.

**File**: `backend/tests/unit/remember/test_unit_of_work.py`

**Intent**: The rollback and the mutual exclusion are behaviour, not wiring.

**Contract**: An exception inside the window leaves all three repositories at their entry
state; a committed window keeps its writes; a second `__aenter__` does not return until the
first `__aexit__` has released the shared lock.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -v`
- `cd backend && uv run ruff check src tests && uv run basedpyright src`

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/remember/contracts -v` and confirm each suite reports
  its cases under the `in_memory` id.
- Confirm two overlapping UoW entries: the second `__aenter__` does not return until the first
  `__aexit__` has released the shared lock.

---

## Phase 10: Review catalog stub

### Overview

Put the catalog's symbol on disk so its contract suite can import it before it does anything.

### Changes Required:

#### 1. Catalog stub

**File**: `backend/src/adapters/out/in_memory/remember/review_catalog.py`

**Contract**: `class InMemoryReviewCatalog` taking `note_repository` and `card_repository`, with
`async def list_reviewable(self) -> Sequence[ReviewableCard]` and
`async def get_reviewable(self, card_id: CardId) -> ReviewableCard | None`. Bodies are `...`.
The port takes no scope argument.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src && uv run basedpyright src`
- `cd backend && uv run python -c "import adapters.out.in_memory.remember.review_catalog"`

#### Manual Verification:
- Confirm both method bodies are `...`.

---

## Phase 11: Fill the catalog and its contract suite

### Overview

Resolve which cards a review may draw on, and the content it renders, without remember
learning anything about distill's model.

### Changes Required:

#### 1. Catalog adapter

**File**: `backend/src/adapters/out/in_memory/remember/review_catalog.py`

**Intent**: The one place a distill card becomes a remember card; a discarded card simply is
not offered.

**Contract**: `list_reviewable()` walks `NoteRepository.list_all()` then
`CardRepository.list_by_note`, keeps `card.discard is None`, and maps each to
`ReviewableCard(id=CardId(value=card.id.value), front=..., back=...)` — remember's own
`CardId`, never distill's type. `get_reviewable(card_id)` returns `None` for an unknown or
discarded card.

#### 2. Contract suite

**File**: `backend/tests/unit/remember/contracts/test_review_catalog_contract.py`

**Intent**: The catalog is a port like any other.

**Contract**: Same `_IMPLEMENTATIONS` shape as the repositories.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -v`
- `cd backend && uv run pytest tests/unit -v` — no distill suite regresses.

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/remember/contracts/test_review_catalog_contract.py -v`
  and confirm a discarded card is absent from both `list_reviewable` and `get_reviewable`.

---

## Phase 12: FSRS dependency and scheduler stub

### Overview

Pin the scheduling library and put the adapter's symbol on disk, so the behaviour phase can be
driven by a repeatability test that imports a real name.

### Changes Required:

#### 1. Dependency

**File**: `backend/pyproject.toml`

**Intent**: Pin the library, because a bump is what invalidates memoized state.

**Contract**: `"fsrs==6.3.2"` added to `[project] dependencies`, then `uv sync`.

#### 2. Adapter stub

**File**: `backend/src/adapters/out/fsrs/__init__.py`, `backend/src/adapters/out/fsrs/scheduler.py`

**Contract**: `class FsrsScheduler` implementing `Scheduler`, with
`def stamp(self) -> SchedulerStamp` and
`def review(self, previous: SchedulingState | None, card_id: CardId, grade: Grade, reviewed_at: datetime) -> SchedulingState`.
Bodies are `...`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv sync`
- `cd backend && uv run ruff check src && uv run basedpyright src`
- `cd backend && uv run python -c "import fsrs; import adapters.out.fsrs.scheduler"`

#### Manual Verification:
- Confirm `uv.lock` records `fsrs==6.3.2` and both method bodies are `...`.

---

## Phase 13: Fill the FSRS scheduler and prove repeatability

### Overview

Put the only code that knows the scheduling library's vocabulary behind the scheduling port,
and make its fuzz reproducible from each event's own recorded facts.

### Changes Required:

#### 1. Adapter

**File**: `backend/src/adapters/out/fsrs/scheduler.py`

**Intent**: Wrap `fsrs` so the domain holds an indexable `due_at` and an opaque blob it never
interprets.

**Contract**: `stamp()` returns
`SchedulerStamp(algorithm=SchedulerAlgorithm.FSRS, parameter_version="fsrs-6.3.2-defaults")`.
`review(previous, card_id, grade, reviewed_at)` builds `fsrs.Card()` on a first review or
`fsrs.Card.from_dict(previous.scheduler_state.payload)` otherwise, maps
`forgot|hard|good|easy` onto `Rating.Again|Hard|Good|Easy`, calls `review_card` with a
timezone-aware UTC `review_datetime`, and returns `SchedulingState` with `due_at` copied off
the returned card and `payload=card.to_dict()`. The fuzz is made deterministic by seeding the
global generator from the event's own facts around the call and restoring it afterwards:

```python
seed = hash((card_id.value, reviewed_at.isoformat(), grade.value))
state = random.getstate()
random.seed(seed)
try:
    reviewed, _ = self._scheduler.review_card(card, rating, review_datetime=reviewed_at)
finally:
    random.setstate(state)
```

The region holds no `await`, so it is atomic against the event loop; a comment must record
that this assumes the port is driven from the loop thread.

#### 2. Repeatability test

**File**: `backend/tests/unit/remember/test_fsrs_scheduler.py`

**Intent**: Prove the frame's reconstruction promise against the real library, fuzz included.

**Contract**: Replaying a card's events through `SchedulingReplay` over `FsrsScheduler`
reproduces the same `due_at` as the sequential live path, for an interval long enough to be
fuzzed.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember -v`
- `cd backend && uv run pytest tests/bdd -m "remember-flow and AC-07" -v`

#### Manual Verification:
- `cd backend && uv run pytest tests/unit/remember/test_fsrs_scheduler.py -v` twice and confirm
  the replayed `due_at` matches across both runs.

---

## Phase 14: HTTP and composition stubs

### Overview

Put the router, its four handlers, and every composition provider on disk as signatures, so the
route tests of the next phase import real names rather than failing on collection.

### Changes Required:

#### 1. Router stub

**File**: `backend/src/adapters/http/remember.py`

**Contract**: `router = APIRouter()` plus four `async def` handlers carrying their final
decorators, paths, response models, and `Depends(...)` parameters, with `...` bodies:
`POST /review-sittings`, `GET /review-sittings/{sitting_id}/current-card`,
`GET /review-sittings/{sitting_id}/cards/{card_id}/back`,
`POST /review-sittings/{sitting_id}/cards/{card_id}/grade`.

#### 2. Composition stubs

**File**: `backend/src/adapters/compose.py`

**Contract**: `get_open_sitting_command`, `get_grade_card_command`, `get_current_card_query`,
`get_reveal_back_query`, and `_remember_unit_of_work` declared with their return annotations
and `...` bodies. No singleton is constructed yet.

**File**: `backend/src/main.py`

**Contract**: `app.include_router(remember_router)`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run ruff check src && uv run basedpyright src`
- `cd backend && uv run python -c "from adapters.http.remember import router"`

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py` and confirm the four routes appear in
  `/docs` — bodies still `...`.

---

## Phase 15: Fill the HTTP surface and composition

### Overview

Expose the sitting over HTTP and wire every seam in `compose.py`, so the slice is a real
tracer bullet rather than a library.

### Changes Required:

#### 1. Router

**File**: `backend/src/adapters/http/remember.py`

**Intent**: The client loop from the contract session — open, then reveal and grade, with a
reread for a request that carries only a sitting id.

**Contract**: `POST /review-sittings` → `SittingOpenedDTO | NothingDueDTO`;
`GET /review-sittings/{sitting_id}/current-card` → `PresentedCardDTO`;
`GET /review-sittings/{sitting_id}/cards/{card_id}/back` → `RevealedCardDTO`;
`POST /review-sittings/{sitting_id}/cards/{card_id}/grade` → `GradeAppliedDTO`. Handlers take
their handler through `Depends(...)` off `adapters.compose`, and return the application DTO
unmapped. No exception is caught here — `core_exception_handler` already maps every remember
code.

#### 2. Composition

**File**: `backend/src/adapters/compose.py`

**Intent**: One place binds settings and adapters; no handler reads the environment.

**Contract**: Module-level singletons for the three repositories, the catalog over the
existing distill repositories, `FsrsScheduler`, `SystemClock`, and one shared `asyncio.Lock`;
`_remember_unit_of_work()` mirrors `_distill_unit_of_work()` and passes that lock.
`ShowingLimit(value=_settings.sitting_max_showings)` is built once and injected into
`OpenSittingCommand` only.

#### 3. Route tests

**File**: `backend/tests/integration/test_remember_routes.py`

**Intent**: Status codes and payload shapes are a contract of their own.

**Contract**: `TestClient` with `dependency_overrides`, asserting the happy loop plus 404 on an
unknown sitting and 409 on grading a card that is not in front.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/integration -v`
- `cd backend && uv run pytest tests/unit/test_http_error_mapping.py -v`
- `cd backend && uv run pytest`

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then
  `curl -X POST localhost:8000/review-sittings` and confirm the response carries a
  `sitting_id`, a `card_id`, and a front with no back.

---

## Phase 16: Migrate the acceptance steps and the handler unit tests onto the real adapters

### Overview

Retire the doubles now that every port has a real in-memory implementation — in the acceptance
step module and in the four handler unit-test modules alike — so both layers prove the
behaviour that actually ships. This phase's deliverable is tests, so it does not go through
`/unit-test`.

### Changes Required:

#### 1. Shared composition

**File**: `backend/tests/integration/support/in_memory_remember.py`

**Intent**: One composition reused by acceptance, integration, and unit suites, as capture and
distill already do.

**Contract**: `InMemoryRememberComposition.create()` returns the three repositories, the
catalog over an in-memory distill pair, `FsrsScheduler`, a fixed clock, the UoW factory over a
shared lock, and the four handlers, plus `dependency_overrides()`.

#### 2. Step module

**File**: `backend/tests/bdd/steps/remember_review.py`

**Intent**: Drive the scenarios through the real adapters.

**Contract**: `_InMemorySittingRepository`, `_InMemoryReviewEventStore`,
`_InMemorySchedulingStateRepository`, `_FakeUnitOfWork` and `_FakeReviewCatalog` are removed in
favour of `InMemoryRememberComposition`. `_FixedClock` stays — it drives the collaborator into a
state the real clock cannot reach on demand. `_FakeScheduler` is removed; the scenarios run on
`FsrsScheduler`, and the AC-07 step asserts a growing interval rather than a multiplier. Step
names and Gherkin text are unchanged.

#### 3. Shared handler fixtures

**File**: `backend/tests/unit/remember/conftest.py`

**Intent**: The four handler modules hand-roll twenty double classes between them — one setup
belongs in one place.

**Contract**: Fixtures building `InMemoryRememberComposition` and each of the four handlers
over it, plus the `ReviewableCard` and `SchedulingState` builders currently duplicated as
module-level `_card_id`, `_reviewable`, `_open_sitting`, `_stamp`, `_state` helpers.

#### 4. Handler unit tests onto the real adapters

**File**: `backend/tests/unit/remember/test_open_sitting_command.py`,
`test_grade_card_command.py`, `test_current_card_query.py`, `test_reveal_back_query.py`

**Intent**: A handler test that passes against a double it also wrote proves the double.

**Contract**: `_Catalog`, `_SittingRepository`, `_ReviewEventStore`,
`_SchedulingStateRepository` and `_UnitOfWork` are removed in favour of the conftest fixtures.
`_Scheduler` and `_RecordingScheduler` give way to `FsrsScheduler` **except** where a test must
force a value the real adapter cannot produce on demand — the stale-stamp path of phase 7
needs a stamp that deliberately mismatches `FsrsScheduler.stamp()`, and a failure path needs a
raising scheduler. Those two cases keep a narrow double, named for what it forces. `_Clock`
stays for the same reason `_FixedClock` does. Test names and assertions are unchanged except
where a real scheduler makes a multiplier assertion meaningless, which becomes a growing
interval as in AC-07.

#### 5. Unit-of-work boundary assertions

**File**: `backend/tests/unit/remember/test_grade_card_command.py`,
`test_open_sitting_command.py`

**Intent**: The doubles never enforced the commit boundary, so nothing today would catch a
handler that commits twice or leaks a write past an exception.

**Contract**: Each command asserts it commits exactly once on the happy path, and that a
raising collaborator leaves all three repositories at their pre-`handle` state. The queries
take no UoW and assert nothing here, per `context/foundation/rules/cqrs-lite.md`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -m "remember-flow" -v` — every scenario green.
- `cd backend && uv run pytest`
- `cd backend && uv run ruff check src tests && uv run basedpyright src`

#### Manual Verification:
- `cd backend && grep -n "_Fake\|_InMemory" tests/bdd/steps/remember_review.py` and confirm only
  `_FixedClock` remains.
- `cd backend && grep -rn "^class _" tests/unit/remember/*.py` and confirm only the doubles that
  force a value `FsrsScheduler` cannot produce survive, each named for what it forces.

---


## Testing Strategy

### Unit Tests:

`backend/tests/unit/remember/`, flat `def test_…` functions named as full sentences, 2–6 per
phase, building their own data through module-private factories. Port contracts live in
`backend/tests/unit/remember/contracts/`, one suite per port, parametrized over
`_IMPLEMENTATIONS` with `ids=["in_memory"]`.

### Integration Tests:

`backend/tests/integration/test_remember_routes.py` over `TestClient`, with the shared
composition in `backend/tests/integration/support/in_memory_remember.py`.

### Manual Testing Steps:

Run the app, open a sitting over a note whose cards distill has generated, reveal a back,
grade it `forgot`, and confirm the same card comes back before the sitting reports complete.

## Performance Considerations

The open path reads every reviewable card and batch-loads their memoized states; with a stale
stamp treated as due, the first sitting after an `fsrs` bump contains the whole backlog. That
is accepted — the frame puts no cap on sitting size. Grading is bounded by one card's event
history, and replay runs only when a stamp mismatches.

## Migration Notes

No data migration: nothing persists yet. `card_is_due` gains a required third parameter, which
touches only `OpenSittingCommand` and its tests. `fsrs==6.3.2` is a new runtime dependency,
pinned in Phase 12; `uv sync` must run there before Phase 13's tests will pass.

## References

- `context/changes/remember-flow-review-session/frame.md`
- `context/changes/remember-flow-review-session/discover-contracts-log.md`
- `context/efforts/remember-flow/{stories,roadmap,research}.md`
- `context/foundation/rules/{layering,cqrs-lite,contract-testing,exceptions,code-ordering}.md`
- `context/foundation/testing-conventions.md`
