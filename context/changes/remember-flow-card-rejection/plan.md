# Card Rejection During Review Implementation Plan

## Overview

A user meeting a bad card in a review can turn it down. The rejection is recorded by
`remember` as a fifth outcome in the same log that already holds grades, and it causes a
`user_audit` discard in `distill` — delivered asynchronously through the existing outbox.
`remember`'s own record closes the window before that discard lands; the `distill` discard
is what actually keeps the card out of every later review.

## Current State Analysis

`remember` has a complete review sitting: `Sitting` draws a card, `RevealBackQuery` shows
its back, `GradeCardCommand` records a `ReviewEvent` and memoizes a `SchedulingState`.
Nothing in it can express "this card is bad".

Four facts constrain how the fifth outcome is added:

- **`Grade` is a total input to the scheduler in two places.** `_RATINGS` in
  `adapters/out/fsrs/scheduler.py:19` is exhaustive over `Grade`, and
  `SchedulingReplay.replay` (`domain/remember/ports.py:99`) folds *every* stored event
  through `Scheduler.review`. A fifth `Grade` member would reach both.
- **`Sitting` is frozen and written once.** `uow.sittings.save` has one call site
  (`application/remember/commands/open_sitting.py:109`) and the port documents the
  aggregate as write-once, so a rejection cannot be a field on the sitting.
- **`remember`'s `UnitOfWork` has no outbox appender.** `capture`'s and `distill`'s do
  (`application/distill/ports.py:16`); remember's carries three repositories only
  (`application/remember/ports.py:17-20`).
- **`distill` has no manual-discard command.** The audit surface
  `context/adrs/distill-domain-shape/decision.md:112` refers to does not exist, and
  `CardRepository` (`domain/distill/ports.py:16`) can only `save` and `list_by_note` — it
  cannot fetch a card by id at all.

On the TUI side the review overlay binds reveal and the four grades in one `useInput`
block (`tui/src/screens/SittingOverlay.tsx:38-80`), and the api layer has no 204 handling
anywhere: every module guards `if (error || !data)` and throws. `currentCard()` does not
exist in `tui/src/api/sittings.ts` — the endpoint is in the backend and the generated
schema but has never been called, because `openSitting` and `gradeCard` return the next
card inline.

## Desired End State

From a card whose back is revealed, one gesture turns it down. The sitting moves to the
next card without ever drawing the rejected one again, and reaches completion without it.
Within a second or so the outbox delivers a `user_audit` discard into `distill`, after
which `InMemoryReviewCatalog` (`adapters/out/in_memory/remember/review_catalog.py:37`)
stops offering the card and no later sitting can contain it.

Verify by walking a sitting in the TUI: reject a card, finish the sitting, open a new
one, and confirm the rejected card is absent. Confirm the reason is distinguishable by
reading the card's `discard.reason` — `user_audit`, not `ungrounded` or `oversized`.

### Key Discoveries:

- `Sitting.visible` is `card_ids & live` and documents that "gone ids drop out"
  (`domain/remember/sitting.py:55-57`) — the catalog is the mechanism that removes a card
  across sittings, and it already filters on `card.discard is None`.
- `Sitting._card_is_finished` (`domain/remember/sitting.py:131`) is the single rule behind
  `is_finished`, `outstanding` and `_eligible_pool` — teaching it about rejection settles
  all three at once.
- `_eligible_pool` (`domain/remember/sitting.py:102`) selects the minimum-showings bucket,
  so a card that produced no event stays the most eligible draw. This is why a purely
  outbox-based rejection leaves `remember` blind for the poll interval
  (`outbox_poll_interval_seconds` defaults to 1.0, `config/settings.py:24`).
- `DiscardReason.USER_AUDIT` already exists (`domain/distill/value_objects.py:108`) and is
  already exercised by a BDD step (`tests/bdd/steps/remember_review.py:393-408`), which
  writes the discard directly rather than through any command.
- `tests/bdd/test_remember_step_coverage.py` reflects over `vars(remember_review)` only —
  new remember-flow steps must be appended to `tests/bdd/steps/remember_review.py`, not to
  a new module.
- `pyproject.toml` registers markers `AC-01` through `AC-15` only; `AC-16` through `AC-23`
  are unregistered.
- `InMemoryRememberComposition` (`tests/integration/support/in_memory_remember.py`) builds
  its own distill `notes`/`cards` repositories and hands them to the catalog, so a
  remember-to-distill round trip can be composed entirely inside it — no cross-fixture
  threading of the kind `tests/bdd/conftest.py:73-77` does for capture-to-distill.
- `tui/src/store/sitting.ts:228-230` pushes a mutation response's `due` partition through
  `useDueStore.applyPartition`, which bumps a generation counter so the 15s poll cannot
  clobber it. A rejection must do the same or the count goes stale.

## What We're NOT Doing

- Restoring a rejected card. A discard is terminal
  (`context/adrs/distill-domain-shape/decision.md:81`).
- Any surface for inspecting or reporting rejections, or for noticing a delivery that was
  abandoned after `max_attempts`.
- Reconciling an abandoned envelope. Rejection is best-effort; if delivery dead-letters,
  the card returns to circulation and the user rejects it again.
- Consulting `remember`'s rejection record as a fallback filter when a later review is
  assembled, or subtracting it from the due count.
- Editing a card during a review. Card wording stays in `distill`.
- Enforcing the reveal gate in the backend. It is a TUI-level convention inherited from
  AC-05 and buys no new machinery.

## Implementation Approach

The fifth outcome is a union, not a fifth grade. `Grade` stays exactly four members, and
`ReviewEvent.grade` widens into `ReviewEvent.outcome: Grade | Rejected`. Everything that
must not see a rejection — `_RATINGS`, `Scheduler.review` — keeps a `Grade` parameter and
therefore cannot be reached by one without a type error. `SchedulingReplay.replay` filters
to `Grade` instances before folding.

`RejectCardCommand` takes no `Scheduler` at all. That absence is the strongest available
statement that rejection produces no scheduling state, and it is checkable by reading one
constructor.

The guard both commands sit behind moves onto the aggregate as `Sitting.guard_outcome`, so
"the moment at which an outcome may be recorded" is one rule in one place rather than two
that can drift.

Delivery reuses the chain that already exists: a `card_rejected` envelope appended in the
same unit of work as the review event, claimed by `OutboxWorker`, handled by a new
`CardDiscardHandler` that delegates to `DiscardCardCommand` in `distill`. The handler is an
adapter, so it may import `domain/remember/outbox` the way `note_save.py` imports
`domain/capture/outbox` — `application/distill/` itself imports nothing from remember.

On the TUI, rejection returns 204 and the client re-reads `current-card`. That needs a new
`currentCard()` in the api module and a 204 branch ahead of the `!data` guard.

## Critical Implementation Details

Phase 1 renames `ReviewEvent.grade` at **21 construction sites across 17 files**, including
the property suite and the BDD step module. The rename is the whole risk of that phase: it
must land in one pass with the suite green, because a half-renamed field type-checks
nowhere.

In `tui/src/api/sittings.ts` the 204 branch must sit **before** the `if (error || !data)`
guard. openapi-fetch leaves `data` undefined on an empty body, so a rejection would
otherwise always fall into `throwOnClientError`, whose error body has no `code` — producing
a generic `Error` on the success path.

`InMemoryRememberComposition.create` must hand the *same* `notes`/`cards` repositories to
both its `InMemoryReviewCatalog` and the distill unit of work behind its discard handler.
Two separate sets would make the handler discard a card the catalog never saw, and AC-17
would pass in the test while failing in production.

---

## Phase 1: Rejection outcome stubs

### Overview

Materialize the fifth outcome and the envelope type it will travel in, and migrate every
existing reader of `ReviewEvent.grade`. No behaviour changes.

### Changes Required:

#### 1. The outcome type

**File**: `backend/src/domain/remember/value_objects.py`

**Intent**: Give the fifth outcome a name that belongs to `remember`. `distill`'s word is
"discard"; borrowing it would name across the boundary this change deliberately does not
write across.

**Contract**: `class Rejected(StrEnum)` with one member `REJECTED = "rejected"`; module
alias `ReviewOutcome = Grade | Rejected`; `FINISHING_OUTCOMES: frozenset[ReviewOutcome]`
holding `Grade.GOOD`, `Grade.EASY` and `Rejected.REJECTED`, replacing `FINISHING_GRADES`.
`Grade` is unchanged and stays four members.

#### 2. The review log entry

**File**: `backend/src/domain/remember/review_event.py`

**Intent**: Carry the outcome of meeting a card, which is now either a grade or a
rejection, in the same log.

**Contract**: `ReviewEvent.grade: Grade` becomes `ReviewEvent.outcome: ReviewOutcome`.
Field order and the other three fields are unchanged.

#### 3. The sitting

**File**: `backend/src/domain/remember/sitting.py`

**Intent**: Read the renamed field, and own the guard both outcome-recording commands sit
behind so the rule cannot drift into two copies.

**Contract**: `_card_is_finished` tests `event.outcome in FINISHING_OUTCOMES`;
`_draw_seed` reads `event.outcome`. New public method
`guard_outcome(self, card_id: CardId, present: frozenset[CardId], events: Sequence[ReviewEvent], as_of: datetime) -> None`,
raising `SittingExpiredError`, `CardNotInSittingError`, `SittingAlreadyCompleteError`,
`CardNotPresentableError` in that order — the order `GradeCardCommand._guard_grade`
already uses.

#### 4. The replay

**File**: `backend/src/domain/remember/ports.py`

**Intent**: Keep a rejection out of the scheduler when a card's state is rebuilt from its
log.

**Contract**: `SchedulingReplay.replay` filters events to those whose `outcome` is a
`Grade` before ordering and folding; returns `None` when nothing survives the filter.

#### 5. The envelope

**File**: `backend/src/domain/remember/outbox.py` (new)

**Intent**: Declare the type and payload rejection travels in, mirroring
`domain/distill/outbox.py`.

**Contract**: `CARD_REJECTED = EnvelopeType(name="card_rejected")`; frozen
`CardRejectedPayload(card_id: UUID, rejected_at: datetime)` with
`to_envelope() -> OutboxEnvelope` returning `OutboxEnvelope.pending(CARD_REJECTED, self.model_dump(mode="json"))`.

#### 6. Call-site migration

**File**: `backend/src/application/remember/commands/grade_card.py`,
`backend/tests/unit/remember/*`, `backend/tests/property/remember/*`,
`backend/tests/bdd/steps/remember_review.py`

**Intent**: Keep the tree green across the rename. `GradeCardCommand` constructs the event
with `outcome=grade` and delegates its guard to `Sitting.guard_outcome`.

**Contract**: 21 `ReviewEvent(...)` construction sites move from `grade=` to `outcome=`.
`_guard_grade` is deleted in favour of the aggregate method.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` is green
- `cd backend && uv run basedpyright src` reports no new errors

#### Manual Verification:
- Grep for `\.grade\b` under `backend/src/domain/remember` and
  `backend/src/application/remember` returns only the `Grade` parameter on `Scheduler`

---

## Phase 2: Rejection settles a card and never reaches the scheduler

### Overview

The two domain behaviours the fifth outcome buys: a rejected card is done for this
sitting, and it never contributes to a schedule.

### Changes Required:

#### 1. Settlement inside the sitting

**File**: `backend/src/domain/remember/sitting.py`

**Intent**: A rejected card counts as settled for the sitting it was rejected in — the
sitting can complete without it, and it is not drawn again.

**Contract**: `is_finished`, `outstanding` and `next_card` all follow from
`_card_is_finished` treating `Rejected.REJECTED` as finishing. A rejection still counts as
a showing in `_showing_count`; the card was met.

#### 2. Replay

**File**: `backend/src/domain/remember/ports.py`

**Intent**: A card whose log holds only rejections has no scheduling state to rebuild, and
a mixed log rebuilds from its grades alone.

**Contract**: `SchedulingReplay.replay` returns `None` for a rejection-only log, and for a
mixed log returns exactly what the same grades alone would have produced.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/test_sitting.py -v`
- `cd backend && uv run pytest tests/unit/remember/test_scheduling_replay.py -v`
- `cd backend && uv run pytest tests/property/remember -v`

### Review r1

Artifact: `reviews/2026-09-11-r1-property-test-phase-2.md`

- SchedulingReplay folds grades belonging to other cards
  Fix: The shrunk two-card log must make `SchedulingReplay.replay(card_a, events)` equal `replay(card_a, events)` with only `card_a` events until the bug is fixed; `test_replay_for_one_card_ignores_another_cards_grades_in_the_sequence` (unit pin) and `test_replay_ignores_grades_belonging_to_other_cards` (property) stay as regression.

### Review r2

Artifact: `reviews/2026-09-11-r2-mutation-test-phase-2.md`

- `R2-F2` — Draw seed must include each event sitting_id in the hash input
  Fix: `_draw_seed` must include each event's real `sitting_id` in the hash input so `next_card` picks change when sitting identity in the log changes.
- `R2-F3` — Draw seed uses exactly eight digest bytes big-endian
  Fix: Draw seed must use exactly the first eight SHA-256 digest bytes (big-endian), not nine.
- `R2-F4` — is_offered is false at exactly opened_at plus resume_horizon
  Fix: `is_offered` must be false at exactly `opened_at + resume_horizon` (strict `<`, not inclusive).

---

## Phase 3: Rejection write-path stubs

### Overview

The command, the route and the composition that will carry a rejection from HTTP into the
review log and the outbox. No behaviour.

### Changes Required:

#### 1. Remember's unit of work

**File**: `backend/src/application/remember/ports.py`,
`backend/src/adapters/out/in_memory/remember/unit_of_work.py`

**Intent**: Write the review event and its envelope atomically. Remember's unit of work
has no outbox today; capture's and distill's do.

**Contract**: `UnitOfWork` gains `outbox: OutboxAppender`. `InMemoryUnitOfWork` takes
`outbox_store: InMemoryOutboxStore` and `outbox: InMemoryOutboxAppender`, snapshots the
store on `__aenter__` and restores it on an uncommitted `__aexit__`, exactly as
`adapters/out/in_memory/distill/unit_of_work.py:37,44` does. The existing `asyncio.Lock`
argument stays last.

#### 2. The command

**File**: `backend/src/application/remember/commands/reject_card.py` (new)

**Intent**: Record a rejection and cause a discard, without touching the schedule.

**Contract**:
```python
class RejectCardCommand:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        catalog: ReviewCatalog,
        clock: Clock,
    ) -> None: ...

    async def handle(self, sitting_id: SittingId, card_id: CardId) -> None: ...
```
No `Scheduler` parameter — the absence is the boundary.

#### 3. Route and production wiring

**File**: `backend/src/adapters/http/remember.py`, `backend/src/adapters/compose.py`

**Intent**: Expose the gesture and build the command with remember's outbox-carrying unit
of work.

**Contract**: `POST /review-sittings/{sitting_id}/cards/{card_id}/rejection`, declared
`status_code=204` and returning `None`. `compose.get_reject_card_command()` added;
`_remember_unit_of_work()` now passes `_outbox_store` and `_outbox_appender`.

#### 4. Test composition seam

**File**: `backend/tests/integration/support/in_memory_remember.py`

**Intent**: Let acceptance and integration tests drive the new route and inspect the
envelope it writes.

**Contract**: `InMemoryRememberComposition` gains `outbox_store: InMemoryOutboxStore` and
`outbox: InMemoryOutboxAppender` fields, a `reject_card()` seam, and
`get_reject_card_command` in `dependency_overrides()`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` is green
- `cd backend && uv run basedpyright src` reports no new errors

#### Manual Verification:
- Start the backend, open a sitting, and
  `curl -i -X POST localhost:8000/review-sittings/<sid>/cards/<cid>/rejection` returns
  `HTTP/1.1 204` with an empty body

---

## Phase 4: Reject command behaviour

### Overview

Guard parity with grading, and the atomic pair of writes.

### Changes Required:

#### 1. The command body

**File**: `backend/src/application/remember/commands/reject_card.py`

**Intent**: Rejection sits behind exactly the gate grading sits behind — one moment of
legality — and produces a review-log entry plus a delivery, together or not at all.

**Contract**: `handle` captures the clock once, loads the sitting and its events, builds
`present` from the catalog, calls `Sitting.guard_outcome`, then writes
`ReviewEvent(card_id, reviewed_at, outcome=Rejected.REJECTED, sitting_id)` and
`CardRejectedPayload(card_id=card_id.value, rejected_at=reviewed_at).to_envelope()` inside
one unit of work before committing. `uow.scheduling_states` is never touched.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/remember/test_reject_card_command.py -v`
- `cd backend && uv run pytest tests/integration/test_remember_routes.py -v`

#### Manual Verification:
- Reject a card via curl, then `curl localhost:8000/_outbox` and confirm one
  `card_rejected` envelope, and that a second read shows it `consumed` rather than
  `pending`

---

## Phase 5: Distill discard stubs

### Overview

The first manual-discard surface in `distill`, and the handler that drives it from the
outbox.

### Changes Required:

#### 1. Fetching a card by id

**File**: `backend/src/domain/distill/ports.py`,
`backend/src/adapters/out/in_memory/distill/card_repository.py`

**Intent**: A discard names one card. The port cannot fetch one today, and remember does
not know `distill`'s `note_id` — the catalog is the only place the two vocabularies meet,
and it deliberately does not carry it back out.

**Contract**: `CardRepository.get(self, card_id: CardId) -> Card | None`. In-memory
implementation reads `self._cards.get(card_id.value)`.

#### 2. The command

**File**: `backend/src/application/distill/commands/discard_card.py` (new)

**Intent**: The `DiscardCard` handler `context/adrs/distill-domain-shape/decision.md:112`
names. General over `DiscardReason`, so the audit surface that comes later reuses it.

**Contract**:
```python
async def handle(
    self,
    card_id: CardId,
    reason: DiscardReason,
    detail: str | None,
    discarded_at: datetime,
) -> None: ...
```
Built from `Callable[[], UnitOfWork]` over distill's own unit of work.

#### 3. The handler

**File**: `backend/src/adapters/out/worker/handlers/card_discard.py` (new)

**Intent**: Consume `card_rejected` and delegate. An adapter may import the producing
context's payload — `note_save.py` imports `domain/capture/outbox` the same way.

**Contract**: `envelope_type: EnvelopeType = CARD_REJECTED`; validates
`CardRejectedPayload`, then calls the command with `DiscardReason.USER_AUDIT`,
`detail=None`, and the payload's `rejected_at`.

#### 4. Production and test wiring

**File**: `backend/src/adapters/compose.py`,
`backend/tests/integration/support/in_memory_remember.py`

**Intent**: Register the handler on the running worker, and give the remember test
composition a worker that drains its own outbox into its own distill repositories.

**Contract**: `compose` builds `DiscardCardCommand` over `_distill_unit_of_work` and
appends `CardDiscardHandler` to `OutboxWorker`'s handler list.
`InMemoryRememberComposition.worker()` composes `InMemoryOutboxClaimer` over its
`outbox_store` with a `CardDiscardHandler` whose distill unit of work uses the **same**
`notes` and `cards` repositories the composition's catalog reads.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` is green
- `cd backend && uv run basedpyright src` reports no new errors

---

## Phase 6: Distill discard behaviour

### Overview

The discard itself, and the three redelivery branches at-least-once delivery makes
reachable.

### Changes Required:

#### 1. The command body

**File**: `backend/src/application/distill/commands/discard_card.py`

**Intent**: Stamp the user's judgement onto the card, and never overwrite a judgement
already recorded. A discard is terminal, and the three reasons are kept disjoint because
each feeds a different correction.

**Contract**: Loads the card; returns after a log line when it is absent or when
`card.discard is not None`, whatever the existing reason; otherwise sets
`Discard(reason=reason, detail=detail, discarded_at=discarded_at)`, saves and commits.
`discarded_at` comes from the envelope, so a redelivery cannot move the timestamp.

#### 2. Payload validation

**File**: `backend/src/adapters/out/worker/handlers/card_discard.py`

**Intent**: A malformed envelope is logged and acked, not retried — the shape
`flashcard_gen.py:20-24` already established.

**Contract**: `ValidationError` is caught, logged with the envelope id, and `handle`
returns without calling the command.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/unit/distill/test_discard_card_command.py -v`
- `cd backend && uv run pytest tests/unit/distill/test_card_discard_handler.py -v`
- `cd backend && uv run pytest tests/unit/distill/contracts/test_card_repository_contract.py -v`

---

## Phase 7: Acceptance layer for AC-17 and AC-23

### Overview

The two acceptance criteria on slice S-04, expressed as scenarios that run the full
remember-to-distill round trip.

### Changes Required:

#### 1. Marker registration

**File**: `backend/pyproject.toml`

**Intent**: `@AC-17` and `@AC-23` are unregistered markers today; the list stops at
`AC-15`. Keep it contiguous rather than punching two holes in it.

**Contract**: Append `AC-16` through `AC-23`, one line each, in the existing
`"AC-nn: acceptance criterion nn"` form.

#### 2. Scenarios and steps

**File**: `backend/tests/features/remember-flow/US-09-turn-down-a-bad-card.feature` (new),
`backend/tests/bdd/steps/remember_review.py`

**Intent**: AC-17 — a rejected card is not offered in any later review. AC-23 — the
rejection is recorded as the user's own judgement, distinguishable from a card the system
rejected at generation time.

**Contract**: Scenarios tagged `@remember-flow @AC-17` and `@remember-flow @AC-23`, one tag
pair per scenario, matching the existing remember-flow feature files. Steps are **appended
to `remember_review.py`** — `tests/bdd/test_remember_step_coverage.py:5` imports only that
module, so a new step module would fail coverage even though pytest-bdd resolves it. The
round trip is driven by a `when` step calling `composition.worker().run_once()`, following
`tests/bdd/steps/distill.py:74-78`. Authored by `/bdd`, not by hand.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd/test_remember_step_coverage.py -v`
- `cd backend && uv run pytest tests/bdd -m "remember-flow" -v` collects without
  `PytestUnknownMarkWarning`

#### Manual Verification:
- Run `/bdd remember-flow-card-rejection` and confirm the two new scenarios fail on
  assertions rather than on undefined steps or collection errors
- Re-run `cd backend && uv run pytest tests/bdd -m "remember-flow"` and confirm no
  previously green scenario turned red

---

## Phase 8: TUI client, store and binding stubs

### Overview

The client functions, store action and key binding the reject gesture needs. No behaviour.

### Changes Required:

#### 1. Generated schema

**File**: `tui/src/api/generated/schema.d.ts`

**Intent**: Pick up the rejection route.

**Contract**: Regenerated with `pnpm generate:api` against a running backend. The file is
generated — no hand edits.

#### 2. Api module

**File**: `tui/src/api/sittings.ts`

**Intent**: Call the rejection endpoint, and read the sitting's current card afterwards —
the review loop has to keep moving, and the rejection response carries no body.

**Contract**: `rejectCard(sittingId: string, cardId: string): Promise<void>` — the 204
branch checks `response.status` **before** the `if (error || !data)` guard, otherwise an
empty body always throws. `currentCard(sittingId: string): Promise<PresentedCard>` maps
`PresentedCardDTO` — `cardId`, `front`, `sittingComplete`, `outstandingCount`, `due`
through `toDuePartition` — reusing `throwOnClientError` for failures.

#### 3. Store action

**File**: `tui/src/store/sitting.ts`

**Intent**: One action the overlay calls, sharing `submitGrade`'s in-flight guard and its
completion tail.

**Contract**: `rejectCurrentCard(): Promise<void>` added to `SittingActions`, guarded by
`isSubmitting`, with `LastAction` extended so `retry()` can replay it.

#### 4. Overlay binding

**File**: `tui/src/screens/SittingOverlay.tsx`

**Intent**: A gesture that only exists once the card has been judged as a pair.

**Contract**: `x` bound inside the existing `useInput` block, after the
`phase === "presented"` early return at line 52, gated on `isBackVisible`. New module
const `REJECT_HINT`, passed to `DueOverlayFooter` alongside `TOGGLE_CARD_HINT`.

#### 5. Test doubles

**File**: `tui/test/sittingOverlay.test.tsx`, `tui/test/sittingStore.test.ts`,
`tui/test/sittingOverlayDueBreakdown.test.tsx`,
`tui/test/implReviewR2F4_submitGradeRace.test.ts`,
`tui/test/implReviewR2F7_toggleBackRace.test.ts`,
`tui/test/implReviewR2F1_outstandingCountFooter.test.tsx`

**Intent**: Every `vi.mock` factory over `src/api/sittings` spreads the real module, so a
new export that is not listed reaches the network.

**Contract**: `rejectCard: vi.fn()` and `currentCard: vi.fn()` added to all six factories.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test` is green
- `cd tui && pnpm build`

#### Manual Verification:
- Run the TUI against a running backend, open a sitting with `/remember`, and confirm
  reveal and the four grades behave exactly as before

---

## Phase 9: Reject client and store behaviour

### Overview

The 204 response, the re-read, and the two pieces of cross-store state a rejection must
keep correct.

### Changes Required:

#### 1. Response mapping

**File**: `tui/src/api/sittings.ts`

**Intent**: A 204 is the success path, not a missing body.

**Contract**: `rejectCard` resolves on 204 and throws `SittingHttpError` carrying `code`
and `detail` on a 4xx, matching `gradeCard`'s error shape.

#### 2. Store transitions

**File**: `tui/src/store/sitting.ts`

**Intent**: After a rejection the overlay shows the next card, the due count stays fresh,
and an expired sitting recovers the way grading already recovers.

**Contract**: `rejectCurrentCard` calls `rejectCard`, then `currentCard(sittingId)`, then
applies the same tail `submitGrade` uses at lines 231-261 — `complete` when
`sittingComplete`, otherwise `presented` with the new front, `isBackVisible` reset to
false, `back` cleared. The response's `due` goes through
`useDueStore.getState().applyPartition`. A `sitting_expired` code routes to
`recoverFromSittingExpired`.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/sittings.test.ts`
- `cd tui && pnpm vitest run test/sittingStore.test.ts`

#### Manual Verification:
- Reject a card in the running TUI and confirm the next card appears without any further
  keystroke, and that the due count in the header does not go stale

---

## Phase 10: Overlay gesture behind the reveal gate

### Overview

The gate itself: a card is judged as a pair, so half of it is not enough to judge on.

### Changes Required:

#### 1. Gated binding and hint

**File**: `tui/src/screens/SittingOverlay.tsx`

**Intent**: Rejection becomes available at exactly the moment grading does, and the hint
appears with it rather than advertising a key that does nothing.

**Contract**: `x` calls `rejectCurrentCard()` only when `isBackVisible` is true and the
phase is `presented`; it is swallowed otherwise. `REJECT_HINT` renders only alongside the
back. ESC, `r`-in-error, `t`, the digits and the arrow/Enter selection are unchanged.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm vitest run test/sittingOverlay.test.tsx`
- `cd tui && pnpm test` is green

#### Manual Verification:
- Walk a full sitting rejecting one card, finish it, open a new sitting with `/remember`,
  and confirm the rejected card is not among the cards offered

---

## Testing Strategy

### Unit Tests:
Domain settlement and replay filtering in `backend/tests/unit/remember/test_sitting.py` and
`test_scheduling_replay.py`. Command behaviour in new
`backend/tests/unit/remember/test_reject_card_command.py`,
`backend/tests/unit/distill/test_discard_card_command.py` and
`test_card_discard_handler.py`. `CardRepository.get` joins the existing contract suite at
`backend/tests/unit/distill/contracts/test_card_repository_contract.py`, which runs
parametrized over implementations. The property suites under
`backend/tests/property/remember/` are migrated in phase 1 and re-run in phase 2.

### Integration Tests:
The rejection route in `backend/tests/integration/test_remember_routes.py`, seeded through
the composition's `notes`/`cards` repositories as the existing tests are. The schema-path
pin in `tui/test/implReviewR1F1_schemaPaths.test.ts` gains the rejection path during
phase 9's test generation.

### Manual Testing Steps:
Per-phase Manual Verification above. The end-to-end walk in phase 10 is the one that
proves AC-17 as a user experiences it.

## Performance Considerations

A rejection adds one envelope per rejected card to a store the worker already polls every
second. `CardRepository.get` replaces what would otherwise be a scan. Nothing here runs in
a loop over the card set.

## Migration Notes

`ReviewEvent.grade` → `outcome` is a rename inside an in-memory store; there is no
persisted data to migrate. Phase 1 must land whole — a partial rename leaves the tree
type-checking nowhere.

## References

- Frame: `context/changes/remember-flow-card-rejection/frame.md`
- Frame log: `context/changes/remember-flow-card-rejection/frame-log.md`
- Slice S-04: `context/efforts/remember-flow/roadmap.md:58-64`
- US-09, AC-17 and AC-23: `context/efforts/remember-flow/stories.md:88-96`
- Discard mechanism and boundary rules: `context/adrs/distill-domain-shape/decision.md:71-112`
- Execution state: `context/changes/remember-flow-card-rejection/todos.md`
