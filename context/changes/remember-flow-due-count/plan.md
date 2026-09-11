# Due Count Implementation Plan

> Execution state lives in `todos.md`, sibling of this file.

## Overview

Users cannot today learn how many cards are waiting without opening a review — and
opening one mints a sitting, which is exactly what AC-14 forbids. This change adds a
read-only reading of the due set: one total of distinct cards waiting, broken down by
*why* each card is waiting, computed by a single pure domain function, carried on every
remember response, and rendered in a shell row that survives an open overlay.

## Current State Analysis

The due predicate already exists and is pure: `card_is_due` and `due_card_ids` at
`backend/src/domain/remember/scheduling_state.py:22-49`. Its only caller today is
`OpenSittingCommand` (`backend/src/application/remember/commands/open_sitting.py:75`),
which writes — `uow.sittings.save` then `uow.commit`. There is no read-only path to the
due set at all.

What a sitting owes is a different set, derived per call and never persisted:
`Sitting.outstanding` (`backend/src/domain/remember/sitting.py:82-96`), projected to
`outstanding_count` at three sites (`open_sitting.py:61,85`, `grade_card.py:124`,
`current_card.py:43`). The two sets diverge in both directions — `Sitting.card_ids` is
frozen at open (`sitting.py:40`) so anything ripening later is due but outside the
sitting, and `_card_is_finished` (`sitting.py:132-139`) retires a card at
`showing_limit` while the schedule may still read it due.

On the TUI side there is no global chrome. `CaptureScreen` owns everything above the
input, and its one persistent element — `WelesBrand` — is budgeted against terminal rows
by `shouldShowWelesBrand` (`tui/src/screens/CaptureScreen.tsx:244-`) and dropped first as
a conversation fills. Both overlays render `position="absolute"` at `top={0} left={0}`,
`width={columns} height={rows}` over `CaptureScreen` (`tui/src/app.tsx`), so they occlude
it completely. Polling precedent exists but is overlay-scoped:
`useNotesPolling` + `notesStore.startPolling` at `NOTES_POLL_INTERVAL_MS = 3000`
(`tui/src/screens/NoteListOverlay.tsx:7`).

## Desired End State

A row at the top of the TUI shows how many cards are waiting, present whether the user is
in a capture conversation, the notes list, or a live review. Inside the review overlay the
same total appears with its breakdown underneath. Every number on screen at one moment
comes from one computation, so no two of them can disagree.

Verify by running the TUI against a live backend: the row shows a count with no sitting
open; opening a review and grading moves the total and the breakdown together; a card
ripening in the background raises the total within one poll interval without any
keystroke.

### Key Discoveries:

- `due_card_ids` / `card_is_due` (`backend/src/domain/remember/scheduling_state.py:22-49`)
  are pure and reusable — a second definition of "due" is the failure this change most
  easily walks into.
- `Sitting.outstanding` and `due_card_ids` answer different questions and neither can
  delegate to the other (`context/changes/remember-flow-due-count/frame-log.md`,
  entry `outstanding-as-source`).
- Remember acceptance steps bypass HTTP and `adapters/compose.py` entirely:
  `backend/tests/bdd/steps/remember_review.py:9` builds `InMemoryRememberComposition`
  from `tests/integration/support/` and calls application handlers directly. The
  acceptance layer therefore needs application symbols and a composition seam, not a
  route.
- `CurrentCardQuery` takes ports directly rather than a `UnitOfWork`
  (`backend/src/application/remember/queries/current_card.py:12-27`) — the pattern this
  change's query follows.
- `outstanding_count: int = 0` on `PresentedCardDTO` and `GradeAppliedDTO`
  (`backend/src/application/remember/dto.py`) is the precedent for additive, defaulted
  DTO growth that does not break the generated TUI client.
- `pnpm generate:api` regenerates `tui/src/api/generated/schema.d.ts` from a *running*
  backend (`tui/package.json`) — it is a manual step, not part of the build.

## What We're NOT Doing

- Minting, resuming, finishing, or otherwise mutating a sitting. Nothing on this path
  writes, and no unit of work commits.
- Changing `FINISHING_GRADES`, `showing_limit`, or what the scheduler returns. The
  scheduler-aware finish rule is carried by
  `context/changes/remember-flow-scheduler-aware-finish/`, parked behind persistence.
- Narrowing or widening "due" below or beyond `card_is_due`. A card with no scheduling
  record is due, exactly as the scheduler has it.
- The post-capture prompt (S-07 / AC-16) and review entry from capture (S-06 / AC-21,
  AC-22).
- Card rejection (S-04) and source jump (S-05).
- A `stories.md` v3. Non-divergence and the breakdown remain design constraints in
  `frame.md` rather than acceptance criteria.

## Implementation Approach

One pure domain function owns the arithmetic. `partition_due` takes the live card ids,
the scheduling states, the open sitting (or `None`) and that sitting's events, and returns
a `DuePartition` of four integers: a total plus three disjoint buckets that sum to it.
It lives beside `due_card_ids` as a module function, not as a `Sitting` method — a method
would have to accept scheduling state, reproducing the exact coupling parked out of scope.

The partition rides on every remember response as a nested `due` object, so a single
computation feeds every number visible at one moment. A new read-only `DueCountQuery`
serves the no-sitting case over the same function.

On the TUI, one store owns the partition. `dueStore` polls the new endpoint every 15
seconds, and `sittingStore` pushes the `due` object out of each `open`/`grade` response
into that same store. The header and the overlay both read from `dueStore`, so there is
exactly one value on screen at any instant. The shell grows a reserved row: the header
renders in `app.tsx` above both overlays, which move to `top={1}` and `height={rows - 1}`.

## Critical Implementation Details

The partition's buckets are decided by two booleans — is the card outstanding in the open
sitting, and has it been shown in that sitting — over the set `due ∪ outstanding`:
`not_yet_seen` = outstanding and unshown, `seen_still_owed` = outstanding and shown,
`ripe_outside_sitting` = everything else. With no sitting live `outstanding` is empty, so
that rule would drop every card into `ripe_outside_sitting`, which has no referent when
there is no sitting. The no-sitting case is therefore an explicit early branch: total in
`not_yet_seen`, the other two zero.

---

## Phase 1: Due partition stubs

### Overview

Materialize the domain symbols the next phase's tests import. No behaviour.

### Changes Required:

#### 1. Due partition module

**File**: `backend/src/domain/remember/due_partition.py`

**Intent**: Give the partition a home beside the due predicate it reuses, so the
arithmetic has one owner and cannot be re-derived elsewhere.

**Contract**: Exports `DuePartition` — a frozen pydantic model with `total: int`,
`not_yet_seen: int`, `seen_still_owed: int`, `ripe_outside_sitting: int` — and the
signature the behaviour phase fills:

```python
def partition_due(
    live_ids: frozenset[CardId],
    states: Mapping[CardId, SchedulingState | None],
    sitting: Sitting | None,
    sitting_events: Sequence[ReviewEvent],
    as_of: datetime,
    current_stamp: SchedulerStamp,
) -> DuePartition: ...
```

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright src/domain/remember/due_partition.py` reports no errors
- `cd backend && uv run pytest tests/unit/remember` still passes

---

## Phase 2: Due partition behaviour

### Overview

Fill `partition_due` and pin its arithmetic — disjointness, the sum invariant, the
no-sitting branch, and the union semantics inside a live sitting.

### Changes Required:

#### 1. Partition arithmetic

**File**: `backend/src/domain/remember/due_partition.py`

**Intent**: Compute the total and its breakdown from one reading of the schedule and the
open sitting together, so every number the caller projects agrees by construction.

**Contract**: With no sitting, the total is `len(due_card_ids(...))` and every card lands
in `not_yet_seen`. With a sitting, the total set is
`due_card_ids(...) | sitting.outstanding(sitting.visible(live_ids), sitting_events)`, and
each member is bucketed by whether it is outstanding and whether it carries at least one
`ReviewEvent` for this sitting. The three buckets are disjoint and sum to `total`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/test_due_partition.py` passes
- `cd backend && uv run pytest tests/unit/remember` passes
- `cd backend && uv run basedpyright src` reports no errors

---

## Phase 3: DTO, query, route and composition stubs

### Overview

Materialize every application, adapter and test-composition symbol the acceptance layer
and the behaviour phases import. No behaviour: the query returns a zero partition and the
route delegates to it.

### Changes Required:

#### 1. Partition DTO and its carriers

**File**: `backend/src/application/remember/dto.py`

**Intent**: Carry the whole partition as one object on every remember response, so a
response can never present half the buckets.

**Contract**: New `DuePartitionDTO` with the four integer fields. New `DueCountDTO` with a
single `due: DuePartitionDTO`. `PresentedCardDTO` and `GradeAppliedDTO` each gain
`due: DuePartitionDTO`, defaulted to a zero partition so the field is additive in the same
way `outstanding_count: int = 0` already is.

#### 2. Due count query

**File**: `backend/src/application/remember/queries/due_count.py`

**Intent**: Serve the count with no sitting in play, on a path that never writes.

**Contract**: `DueCountQuery.__init__(sittings, events, catalog, scheduling_states, clock,
scheduler)` — ports injected directly, following `CurrentCardQuery`, not a `UnitOfWork`.
`async def handle(self) -> DueCountDTO`.

#### 3. Route and production wiring

**File**: `backend/src/adapters/http/remember.py`, `backend/src/adapters/compose.py`

**Intent**: Expose the reading at a path that does not sit under `/review-sittings`,
because it does not depend on a sitting existing.

**Contract**: `GET /due-cards/count -> DueCountDTO`, backed by a
`get_due_count_query()` factory composed from the existing remember singletons.

#### 4. Acceptance composition seam

**File**: `backend/tests/integration/support/in_memory_remember.py`

**Intent**: Give the acceptance steps the same access to the query they already have to
the four existing handlers.

**Contract**: `def due_count(self) -> DueCountQuery`, matching the shape of
`open_sitting()`, `grade_card()`, `current_card()` and `reveal_back()`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run basedpyright src tests` reports no errors
- `cd backend && uv run pytest` passes
- `cd backend && uv run python -c "from adapters.compose import get_due_count_query; get_due_count_query()"` constructs

#### Manual Verification:
- `cd backend && uv run uvicorn main:app` then `curl localhost:8000/due-cards/count` returns a zero partition with HTTP 200

### Review r4

Artifact: `reviews/2026-09-11-r4-impl-review.md`

- `R4-F2` — Three phases verify with a checker this project does not install
  Fix: a phase's Automated Verification bullet must name a command this repository can
  actually run. Correct the `uv run pyright` bullets on Phases 1, 2 and 3 to the installed
  checker (`basedpyright`) rather than adding a `pyright` shim or dependency to satisfy the
  prose.

---

## Phase 4: Acceptance layer for AC-14 and AC-15

### Overview

Author the US-07 scenarios through `/bdd`, against symbols that now exist, so the
scenarios fail on assertions rather than on imports. They stay red until Phase 5.

### Changes Required:

#### 1. US-07 feature and steps

**File**: `backend/tests/features/remember-flow/US-07-see-what-is-waiting-without-sitting-down.feature`,
`backend/tests/bdd/steps/remember_review.py`

**Intent**: Give AC-14 and AC-15 acceptance authority on the backend half of what they
assert.

**Contract**: AC-14 — reading the count leaves no sitting stored, asserted against
`composition.sittings.latest()` after the read. AC-15 — a card whose `due_at` passes
between two reads raises the total on the second, driven by the existing `_FixedClock`
advance seam. The polling tick itself is a TUI concern and is not asserted here.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -k US_07` collects the new scenarios
- `cd backend && uv run pytest tests/bdd -k "not US_07"` passes — no existing scenario regressed

#### Manual Verification:
- Confirm the new scenarios fail on assertions, not on collection or import errors

---

## Phase 5: Due count query and route behaviour

### Overview

Make the query compute a real partition and turn the US-07 scenarios green.

### Changes Required:

#### 1. Query behaviour

**File**: `backend/src/application/remember/queries/due_count.py`

**Intent**: Assemble the four readings and call the partition function once.

**Contract**: Reads `catalog.list_reviewable()`, `scheduling_states.get_many(...)`,
`sittings.latest()` and — when that sitting is still offered — its events, then returns
`partition_due(...)` wrapped in `DueCountDTO`. A sitting past its resume horizon is
treated as absent. No write, no commit, on any branch.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/test_due_count_query.py` passes
- `cd backend && uv run pytest tests/integration/test_remember_routes.py` passes
- `cd backend && uv run pytest tests/bdd` passes — US-07 now green

#### Manual Verification:
- `curl localhost:8000/due-cards/count` against a backend seeded with cards returns a non-zero total with the breakdown summing to it

---

## Phase 6: Partition on sitting responses

### Overview

Make `open`, `grade` and `current-card` carry the same partition, so one interaction
refreshes every number on screen from one computation.

### Changes Required:

#### 1. The three sitting handlers

**File**: `backend/src/application/remember/commands/open_sitting.py`,
`backend/src/application/remember/commands/grade_card.py`,
`backend/src/application/remember/queries/current_card.py`

**Intent**: Remove the second update path for numbers the boundary requires to agree —
a header refreshed by polling beside an overlay refreshed by a grade response would
disagree between ticks.

**Contract**: Each handler calls `partition_due` once, on state it has already loaded, and
sets `due` on the DTO it returns. `outstanding_count` keeps its current meaning and is not
removed from the DTOs.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember` passes
- `cd backend && uv run pytest tests/integration/test_remember_routes.py` passes
- `cd backend && uv run pytest` passes

#### Manual Verification:
- `curl -X POST localhost:8000/review-sittings` returns a `due` object whose `seen_still_owed` is zero on a freshly minted sitting, and non-zero after a `hard` grade

---

## Phase 7: TUI API client and due store stubs

### Overview

Regenerate the client schema and materialize the TUI symbols the behaviour phase's tests
import.

### Changes Required:

#### 1. Generated schema

**File**: `tui/src/api/generated/schema.d.ts`

**Intent**: Teach the generated client about the new route and the nested `due` object.

**Contract**: Regenerated by `pnpm generate:api` against a running backend — never edited
by hand.

#### 2. Due API module and store

**File**: `tui/src/api/due.ts`, `tui/src/store/due.ts`, `tui/src/hooks/useDuePolling.ts`

**Intent**: Give the partition one owner on the client side.

**Contract**: `api/due.ts` exports `type DuePartition = { total, notYetSeen,
seenStillOwed, ripeOutsideSitting }` and `fetchDueCount(): Promise<DuePartition>`.
`store/due.ts` exports `useDueStore` holding `partition: DuePartition | null`,
`isStale: boolean`, plus `fetchDue`, `applyPartition`, `startPolling`, `stopPolling` —
the `notesStore` polling shape. `useDuePolling(intervalMs)` mirrors `useNotesPolling`.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck` reports no errors
- `cd tui && pnpm test` passes
- `cd tui && pnpm lint` passes

#### Manual Verification:
- Run `pnpm generate:api` against a live backend and confirm the diff carries `/due-cards/count` and the nested `due` object on the sitting responses

---

## Phase 8: Due client and store behaviour

### Overview

Fill the mapping, the polling lifecycle, the stale-on-error rule, and the single-source
reconciliation between polling and sitting responses.

### Changes Required:

#### 1. Response mapping

**File**: `tui/src/api/due.ts`, `tui/src/api/sittings.ts`

**Intent**: Map the nested snake_case partition once, in one helper both modules use.

**Contract**: A shared `toDuePartition(raw)` maps `due.total`, `due.not_yet_seen`,
`due.seen_still_owed`, `due.ripe_outside_sitting`. `openSitting` and `gradeCard` return
`due` alongside their existing fields.

#### 2. Store behaviour

**File**: `tui/src/store/due.ts`, `tui/src/store/sitting.ts`

**Intent**: Make one store the only source of the partition, so the header and the overlay
cannot show two different truths.

**Contract**: A successful fetch sets `partition` and clears `isStale`; a failed fetch
leaves `partition` untouched and sets `isStale` — the header keeps its last number,
dimmed. `startPolling` fetches immediately then on interval and is idempotent, clearing any
prior handle exactly as `notesStore.startPolling` does. `sittingStore.open` and
`sittingStore.submitGrade` call `useDueStore.getState().applyPartition(due)` on every
successful response.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test` passes
- `cd tui && pnpm typecheck` reports no errors

#### Manual Verification:
- Stop the backend with the TUI running and confirm the header keeps its last number rather than clearing, then restore the backend and confirm it un-dims

### Review r4

Artifact: `reviews/2026-09-11-r4-impl-review.md`

- `R4-F1` — A poll answering after a grade overwrites the fresher partition
  Fix: the store's partition must never move backwards in time — a `fetchDue` result may
  only be written when no newer partition has been applied since that request left. Order
  the writes; do not lengthen or shorten the poll interval to hide the window.

---

## Phase 9: Shell row and overlay geometry

### Overview

Add the reserved header row above both overlays and move the overlays down to make space.

### Changes Required:

#### 1. Header component and shell geometry

**File**: `tui/src/app.tsx`, `tui/src/components/DueCountHeader.tsx`

**Intent**: Put the total where it survives an open overlay. The `WelesBrand` slot cannot
carry it — `shouldShowWelesBrand` (`tui/src/screens/CaptureScreen.tsx:244-`) drops that
block first as a conversation fills, which is exactly when the number matters most.

**Contract**: `DueCountHeader` renders one line from `useDueStore`, dimmed when `isStale`
and rendering nothing when `partition` is still `null`. `app.tsx` mounts it as the first
child, calls `useDuePolling(DUE_POLL_INTERVAL_MS)` with a module constant of `15000`, and
both overlay boxes move from `top={0} height={rows}` to `top={1} height={rows - 1}`.

#### 2. Existing shell tests

**File**: `tui/test/app.test.tsx`, `tui/test/noteListOverlay.test.tsx`,
`tui/test/sittingOverlay.test.tsx`

**Intent**: These three suites rest on the current full-screen geometry and must move with
it.

**Contract**: Assertions that depend on overlay position or height are updated to the
shifted geometry; the behaviours they assert are unchanged.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test` passes
- `cd tui && pnpm typecheck` reports no errors
- `cd tui && pnpm lint` passes

#### Manual Verification:
- Run the TUI against a live backend, open the notes overlay and the review overlay in turn, and confirm the count row stays visible and correct in both

---

## Phase 10: Breakdown in the sitting overlay

### Overview

Replace the overlay's lone outstanding count with the total and its breakdown.

### Changes Required:

#### 1. Overlay footer

**File**: `tui/src/screens/SittingOverlay.tsx`

**Intent**: Show *why* cards are waiting where the user is acting on them, without putting
two addable numbers side by side.

**Contract**: The footer's `{outstandingCount} left` (`SittingOverlay.tsx:27` and its
render site) is replaced by the total from `useDueStore` with the non-zero buckets
rendered beneath it. The breakdown renders only when a bucket other than `not_yet_seen`
is non-zero.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test` passes
- `cd tui && pnpm typecheck` reports no errors

#### Manual Verification:
- Grade a card `hard` in a live review and confirm the overlay total and the header total move together and never disagree

### Post-phase polish (conscious, after live TUI review)

These adjustments deliberately extend Phase 9–10 UX without changing backend contracts or
`dueStore` semantics. They are not plan drift — they respond to manual review of readability
and shell geometry.

- **Shell row position** (`tui/src/app.tsx`): the deck-wide total moves from a reserved top
  row to the **bottom** of the terminal (yellow), matching the overlay footer anchor. Overlays
  use the upper `rows - 1`; the shell due line stays visible under the notes overlay and is
  **hidden during review** so the sitting overlay footer is the single due surface (no duplicate
  total).
- **Overlay footer component** (`tui/src/components/DueOverlayFooter.tsx`,
  `tui/src/lib/dueFormat.ts`): breakdown buckets render as **count + inline description** on one
  line (cyan count, dim description), not a separate legend block. Copy names user-visible
  meaning (`not yet shown in this review`, `graded, still in this review`, `due outside this
  review`) instead of internal bucket names. Toggle hint stays yellow, separated by margin from
  due lines.

---

## Testing Strategy

### Unit Tests:

- `backend/tests/unit/remember/test_due_partition.py` — disjointness, the sum invariant,
  the no-sitting branch, cards with no scheduling record, and a card that is outstanding
  but no longer due.
- `backend/tests/unit/remember/test_due_count_query.py` — the query writes nothing on
  every branch, and treats a sitting past its resume horizon as absent.
- `tui/test/dueStore.test.ts`, `tui/test/due.test.ts` — mapping, polling lifecycle,
  stale-on-error retention, and `applyPartition` from sitting responses.

### Integration Tests:

- `backend/tests/integration/test_remember_routes.py` — `GET /due-cards/count` shape and
  status, and the `due` object on the three sitting responses.

### Manual Testing Steps:

1. `cd backend && uv run uvicorn main:app`
2. `cd tui && pnpm build && pnpm start`
3. Confirm the count row is present with no review open.
4. Open a review, grade a card `hard`, and confirm the header total and the overlay
   breakdown move together.
5. Leave the TUI idle past a card's `due_at` and confirm the total rises within 15
   seconds without a keystroke.

## Performance Considerations

The header polls every 15 seconds for the whole session lifetime, against the notes
overlay's 3 seconds while open. Each read walks the full reviewable catalog and its
scheduling states — the same work `OpenSittingCommand` already does per open, on an
in-memory store.

## Migration Notes

`due` is additive and defaulted on `PresentedCardDTO` and `GradeAppliedDTO`, so a TUI
built before this change keeps working against a backend carrying it. The generated
`schema.d.ts` must be regenerated against a running backend (Phase 7) before the TUI
phases typecheck.

## References

- `context/changes/remember-flow-due-count/frame.md` — boundaries and requirements
- `context/changes/remember-flow-due-count/frame-log.md` — the decisions behind them
- `context/efforts/remember-flow/stories.md` — US-07, AC-14, AC-15
- `context/efforts/remember-flow/roadmap.md` — slice S-03
- `context/changes/remember-flow-scheduler-aware-finish/` — the parked aggregate defect
