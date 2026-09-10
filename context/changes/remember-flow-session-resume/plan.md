# Remember Flow Session Resume Implementation Plan

## Overview

Make a review sitting survivable: a user who walks away mid-review comes back — silently, to
the same sitting, with the cards it still holds outstanding — for as long as that sitting is
inside its resume horizon. Past the horizon the sitting stops being a workable thing: opening a
review mints a fresh one over what is due at that moment, and any handle still holding the old
`sitting_id` is refused. Covers AC-10 through AC-13 of the `remember-flow` effort, across both
the backend and the TUI.

## Current State Analysis

The contract-shaping session (`discover-contracts.md`, `status: closed`) already put the resume
half of this change into the working tree. What remains is unevenly distributed, and the split
matters for how the phases below are shaped.

**Already on disk — the resume path:**

- `domain/remember/sitting.py:26` — `Sitting.resume_horizon`, snapshotted at open beside
  `showing_limit`, so a later settings change never retro-shortens a live sitting.
- `domain/remember/sitting.py:98-100` — `is_offered(as_of)`, deriving
  `as_of < opened_at + resume_horizon.value`. There is no stored `expires_at` and no
  `closed_at`; both were argued down in the shaping session as second copies of a derivable fact.
- `domain/remember/sitting.py:82-93` — `outstanding(present, events)`, the unfinished-member set
  whose size is the count the frame requires the user to see.
- `domain/remember/value_objects.py:81-99` — `MIN_RESUME_HORIZON = timedelta(days=1)` and the
  `ResumeHorizon` VO, strictly positive. The day is documented there as the *planned Settings
  default*, explicitly not a type floor.
- `domain/remember/ports.py:33-39` — `SittingRepository.latest()`, plus its in-memory
  implementation at `adapters/out/in_memory/remember/sitting_repository.py:16-19`.
- `application/remember/dto.py:25-26` — `SittingResumedDTO` with `kind="resumed"`, and
  `outstanding_count` on both `PresentedCardDTO:18` and `GradeAppliedDTO:43`.
- `adapters/http/remember.py:30-34` — `POST /review-sittings` already returns the three-way union
  `SittingOpenedDTO | SittingResumedDTO | NothingDueDTO`.
- `application/remember/commands/open_sitting.py:26,33-35` — `OpenSittingCommand` already accepts
  a `resume_horizon` constructor argument, falling back to `MIN_RESUME_HORIZON`.

**Not on disk at all — the expiry path.** Verified absent across `src` and `tests`:
`SittingExpiredError`, any `sitting_expired` entry in `EXCEPTION_STATUS_MAP`, a `Clock` parameter
on `CurrentCardQuery.__init__` (`queries/current_card.py:10-18`, takes `sittings, events,
catalog`) or `RevealBackQuery.__init__` (`queries/reveal_back.py:11-18`, takes
`sittings, catalog`), and `sitting_resume_horizon_hours` in `Settings`. This is not an oversight:
the shaping session parked `by-id-after-expiry` for `/plan` by name, because the decision had not
been made yet.

### Key Discoveries:

- `application/remember/commands/open_sitting.py:60-80` — the live `handle()` body is still
  S-01's mint-only path. The convergent-resume contract exists only as prose in its docstring
  (`:41-53`), deliberately left there so working code was never deleted for a shape.
- `domain/remember/scheduling_state.py:34-48` — `due_card_ids` has **zero callers** anywhere in
  `src` or `tests`. It was written for the since-rejected `DueCountQuery`, and the shaping log
  asserts it "stays as the mint path's due set for `OpenSittingCommand`" — but the mint path
  inlines its own `card_is_due` comprehension instead. Two definitions of due-ness, one of them
  dead and one of them undocumented.
- `tests/bdd/steps/remember_review.py:49-56` — `_FixedClock` holds a single immutable `moment`
  with no way to advance it. AC-12 (a sitting aging past its horizon) is currently
  **inexpressible** in the acceptance layer.
- `tests/integration/support/in_memory_remember.py:50-67` — `InMemoryRememberComposition.create`
  takes `clock` and `showing_limit` but no `resume_horizon`, so no test can mint a sitting with a
  horizon short enough to cross.
- `config/settings.py:24,30` — the settings convention is a scalar with its unit in the field
  name (`outbox_poll_interval_seconds: float`, `sitting_max_showings: int`). No `timedelta` field
  exists in the file.
- `adapters/http/errors.py:53-57` — the error handler maps `CoreException.code()` to a status
  and never imports a concrete exception class. A repo-wide exhaustiveness test walks
  `CoreException.__subclasses__()` and fails on any code missing from the table, so a new
  exception without a map entry is caught automatically.
- `tui/src/api/sittings.ts:107-119` — `throwOnClientError` already turns any `{code, detail}`
  body into a `SittingHttpError` carrying `code`. A new backend error code needs no transport
  work in the TUI; only the store's reaction to it is new.
- `tui/package.json:19` — `pnpm generate:api` regenerates `src/api/generated/schema.d.ts` from a
  **running** backend at `localhost:8000`. Schema regeneration is therefore a manual step
  requiring a live server, not something an agent can run unattended.

## Desired End State

Opening a review is the single re-entry gesture. `POST /review-sittings` finds a sitting that is
still offered and unfinished and returns it as `resumed` — no new sitting is written, no card set
is recomputed against the current moment. The TUI shows that the user is returning, and how many
cards remain, and keeps the count current as they grade.

Past the horizon, that same gesture mints a fresh sitting over what is due now — which naturally
re-collects the cards left ungraded in the expired one, because an ungraded card wrote no review
event and so never moved its `SchedulingState`. Any request still carrying the stale
`sitting_id` — grade, current-card, or reveal-back — is refused with `409 sitting_expired`. The
TUI treats that one code as a recovery signal rather than an error: it opens a fresh sitting and
tells the user once that the previous one expired.

Verify with: `cd backend && uv run pytest` green (including `tests/bdd -m "remember-flow"`), and
`cd tui && pnpm test && pnpm typecheck` green, plus the manual recipes in each phase.

## What We're NOT Doing

- **No `expires_in` / `expires_at` on any DTO.** The 409 stays the single authority on
  expiry. A client-side countdown would be a second mechanism needing clock agreement and
  surviving process suspension, and `expires_at` remains a pure derivation of
  `opened_at + resume_horizon` so nothing is foreclosed by deferring it.
- **No change to the URL shape.** `sitting_id` stays in the path for grade, current-card and
  reveal-back — it is the axis a future grade-per-topic will branch on, so removing it now would
  only mean reintroducing it later under another name.
- **No "start fresh" mode** that abandons an unexpired sitting — the frame put it out of scope.
- **No close command and no stored close stamp.** Finish stays derived from the event log;
  `OpenSittingCommand` remains the sole writer of the aggregate.
- **No due-count query.** `DueCountQuery` / `DueCountDTO` were rejected in shaping; AC-14/AC-15
  belong to S-03 (`remember-flow-due-count`).
- **No server-side auto-mint on a by-id call.** A `POST .../cards/{id}/grade` must never create
  an aggregate as a side effect.
- **No ownership or authentication.** No owner key on sittings, cards, events or scheduling
  state.
- **No SQL adapter.** The in-memory adapter remains the only implementation, per InMemoryFirst.

## Implementation Approach

Acceptance layer first, per this repo's convention — the scenarios for AC-10…AC-13 are authored
by `/bdd` as Phase 1 and must be red on assertions before any production code moves. That phase
also carries the two pieces of test infrastructure without which AC-12 cannot even be written: an
advanceable `_FixedClock` and a `resume_horizon` seam on the test composition.

Backend then proceeds settings-first (Phase 2), convergent open (Phase 3), expiry guard
(Phases 4-5). The TUI follows bottom-up in the layering S-01 established — API client, then
store, then screen.

**Per-unit testability verdicts.** `discover-contracts.md` is closed, so the stubs-then-behavior
pairing is dropped *where the architecture is genuinely already in the tree*: Phase 3 rewrites a
method body against symbols that all exist, and Phase 10 touches a component that gains no new
export — both are single behavior phases. The expiry path is the exception. Its symbols do not
exist, precisely because shaping parked the decision for this plan, so Phases 4-5 keep the
pairing. The TUI keeps it throughout (Phases 6-7, 8-9): the shaping session never touched
`tui/`.

```
POST /review-sittings ──▶ OpenSittingCommand.handle
                              │
              ┌───────────────┴────────────────┐
        latest() offered                 else mint
        and unfinished                due_card_ids(...)
              │                              │
      SittingResumedDTO              SittingOpenedDTO / NothingDueDTO
              │                              │
              └──────────┬───────────────────┘
                         ▼
              tui store/sitting.ts  ──(409 sitting_expired)──▶ re-open + notice
                         │
                 SittingOverlay.tsx  ── "Resumed" (one-shot) + "N left" (persistent)
```

## Critical Implementation Details

A sitting freezes its membership at open — `card_ids` is a `frozenset` on a `frozen=True` model,
and `visible(live)` only ever *intersects* with the live catalog. Cards that become due while a
sitting is alive therefore cannot join it. Expiry is consequently not merely cleanup: it is the
only valve through which newly-due cards enter a review at all. Shortening the horizon opens that
valve more often; lengthening it starves new material.

## Phase 1: Acceptance layer for AC-10 through AC-13

### Overview

Author the scenarios for silent resume and horizon expiry, and give the acceptance harness the
two capabilities it currently lacks — an advanceable clock and a configurable horizon. This phase
authors tests only; it is `/bdd`'s work.

### Changes Required:

#### 1. Advanceable test clock

**File**: `backend/tests/bdd/steps/remember_review.py`

**Intent**: AC-12 requires a sitting to age past its horizon; the current fixed clock cannot
reach that state, so the behaviour is inexpressible today.

**Contract**: `_FixedClock` gains a mutation that moves its moment forward, leaving `now()`
unchanged in signature so every existing step keeps working.

```python
def advance(self, delta: timedelta) -> None:
    self._moment = self._moment + delta
```

#### 2. Horizon seam on the test composition

**File**: `backend/tests/integration/support/in_memory_remember.py`

**Intent**: Scenarios must mint sittings with a horizon short enough to cross deliberately.

**Contract**: `InMemoryRememberComposition` gains a `resume_horizon: ResumeHorizon` field and
`create(...)` a matching optional keyword, defaulting to `ResumeHorizon(value=MIN_RESUME_HORIZON)`.
`open_sitting()` passes it to `OpenSittingCommand`.

#### 3. Resume scenarios

**File**: `backend/tests/features/remember-flow/US-05-pick-up-where-you-left-off.feature`

**Intent**: AC-10 and AC-11 — grades given before leaving still count, and returning continues
with the cards still outstanding.

**Contract**: Scenarios tagged `@remember-flow @AC-10` and `@remember-flow @AC-11`. Cover:
grading one card of a multi-card sitting then re-opening returns `kind: "resumed"`; the resumed
sitting carries the same `sitting_id`; its `outstanding_count` excludes the already-finished
card; a card graded good before leaving is not presented again after returning; re-opening writes
no second sitting.

#### 4. Expiry scenarios

**File**: `backend/tests/features/remember-flow/US-06-what-is-offered-is-worth-resuming.feature`

**Intent**: AC-12 and AC-13 — a sitting left long enough is no longer offered, and grades from it
still count toward the schedule.

**Contract**: Scenarios tagged `@remember-flow @AC-12` and `@remember-flow @AC-13`. Cover:
advancing past the horizon then opening yields `kind: "opened"` with a new `sitting_id`; a card
left ungraded in the expired sitting appears in the fresh one; a card graded good in the expired
sitting keeps its future due date and is absent from the fresh one; the fresh sitting's per-card
showing counts start over.

#### 5. Step definitions

**File**: `backend/tests/bdd/steps/remember_review.py`

**Intent**: Drive the new phrases through the existing in-memory composition.

**Contract**: Steps for opening with a named short horizon, advancing the clock beyond it,
asserting the `kind` discriminator, asserting `outstanding_count`, and asserting sitting-id
identity or difference across two opens. `RememberFlowContext` already carries
`prior_sitting_id` and `last_open_result` for the comparison.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -m "remember-flow" -v` collects every new scenario with
  no `StepDefinitionNotFoundError`
- `cd backend && uv run pytest tests/bdd -m "remember-flow and (AC-10 or AC-11 or AC-12 or AC-13)"`
  fails on assertions, not on collection or import
- `cd backend && uv run pytest tests/bdd -m "remember-flow and not (AC-10 or AC-11 or AC-12 or AC-13)"`
  stays green — the clock change breaks no existing scenario

#### Manual Verification:
- Run `/bdd remember-flow-session-resume` and confirm each new scenario carries an AC tag drawn
  from `stories.md`, and that no scenario asserts a mechanism the frame left unnamed

---

## Phase 2: Settings and composition wiring

### Overview

Make the resume horizon a configured value rather than a constant baked into the command's
fallback.

### Changes Required:

#### 1. Settings field

**File**: `backend/src/config/settings.py`

**Intent**: The horizon is configuration, not an invariant — shaping settled that the one-day
value is a default, and the VO's only rule stays "strictly positive".

**Contract**: `sitting_resume_horizon_hours: float = 24.0`, beside `sitting_max_showings`.
Hours, in the field name, per the file's existing unit-in-the-name convention; a float so a
sub-day horizon needs no type change.

#### 2. Compose the VO

**File**: `backend/src/adapters/compose.py`

**Intent**: Wrap the setting once at the edge so no command ever reads env, mirroring
`_remember_showing_limit`.

**Contract**: A module-level `_remember_resume_horizon = ResumeHorizon(value=timedelta(hours=_settings.sitting_resume_horizon_hours))`,
passed as `resume_horizon=` in `get_open_sitting_command()`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest` green
- `cd backend && uv run pyright` clean

#### Manual Verification:
- `cd backend && SITTING_RESUME_HORIZON_HOURS=0 uv run python -c "from adapters import compose"`
  raises `InvalidResumeHorizonError` — the VO, not the settings type, is the guard
- `cd backend && uv run fastapi dev src/main.py` boots with no env override set

---

## Phase 3: Convergent open returns a resumable sitting

### Overview

Replace the mint-only body of `OpenSittingCommand.handle` with the convergent flow its docstring
has been describing, and collapse the two definitions of due-ness into one.

### Changes Required:

#### 1. Convergent open

**File**: `backend/src/application/remember/commands/open_sitting.py`

**Intent**: Opening a review is the sole re-entry point; the command — not a stored pointer and
not the client — is both the uniqueness guard and the silent return.

**Contract**: `handle()` keeps its signature and return union. Inside the unit of work, before
the due computation: load `latest()`; when present and `is_offered(as_of)` and not
`is_finished(visible, events)`, return `SittingResumedDTO` built from that sitting's own
`next_card`, `outstanding`, and `is_finished` — **without saving anything**. Otherwise fall
through to the existing mint path. The prose contract in the docstring is replaced by the code
that now implements it.

#### 2. One definition of due-ness

**File**: `backend/src/application/remember/commands/open_sitting.py`

**Intent**: `due_card_ids` is currently dead while the mint path carries its own copy of the same
rule; with mint now reachable twice (first open, and re-mint after expiry) the duplication is
worth closing before S-03 adds a third.

**Contract**: The inline `frozenset(... card_is_due ...)` comprehension is replaced by
`due_card_ids(frozenset(by_id), states, as_of, live_stamp)`. `card_is_due` stays the primitive;
`due_card_ids` becomes its only application-facing caller.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -m "remember-flow and (AC-10 or AC-11)"` green
- `cd backend && uv run pytest tests/bdd -m "remember-flow"` green — S-01 scenarios unaffected
- `cd backend && uv run pytest` green
- `cd backend && uv run pyright` clean
- `cd backend && grep -rn "card_is_due" src/application` returns no hits — the rule lives in the
  domain helper only

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then `curl -X POST localhost:8000/review-sittings`
  twice in a row: the second response carries `"kind": "resumed"` and the same `sitting_id`

---

## Phase 4: Expiry stubs

### Overview

Materialize the symbols the expiry guard needs. No guard logic — signatures, the exception, and
its status mapping only.

### Changes Required:

#### 1. The exception

**File**: `backend/src/domain/remember/exceptions.py`

**Intent**: A sitting past its horizon is not a workable sitting; refusing by-id work needs a
code of its own so the adapter can map it without importing the class.

**Contract**: `class SittingExpiredError(CoreException)` — deriving code `sitting_expired` from
its name, no explicit override.

#### 2. Status mapping

**File**: `backend/src/adapters/http/errors.py`

**Intent**: Conflict with current state, not a missing resource — the sitting exists, it is
simply no longer workable.

**Contract**: `"sitting_expired": 409` in `EXCEPTION_STATUS_MAP`.

#### 3. Clock on the read handlers

**File**: `backend/src/application/remember/queries/current_card.py`,
`backend/src/application/remember/queries/reveal_back.py`

**Intent**: Both must judge the horizon, and neither can reach a clock today.

**Contract**: Each `__init__` gains a trailing `clock: Clock` parameter stored as `self._clock`.
`Clock` is imported from `application.remember.ports`. Handler bodies are unchanged in this
phase. Query handlers still receive no `UnitOfWork` and never commit, per CQRS-lite.

#### 4. Wire the new parameter

**File**: `backend/src/adapters/compose.py`,
`backend/tests/integration/support/in_memory_remember.py`

**Intent**: Keep both compositions constructing successfully across the signature change.

**Contract**: `get_current_card_query()` and `get_reveal_back_query()` pass `_remember_clock`;
`InMemoryRememberComposition.current_card()` and `.reveal_back()` pass `self.clock`.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pyright` clean — every construction site updated
- `cd backend && uv run pytest tests/unit tests/integration` green — no behaviour changed yet
- `cd backend && uv run pytest tests/unit -k exhaustive` green — the code-to-status
  exhaustiveness test accepts the new subclass

---

## Phase 5: Expiry refuses work by sitting id

### Overview

Make the three by-id handlers refuse a sitting past its horizon, and leave the client to recover
by opening a new one.

### Changes Required:

#### 1. Guard the write

**File**: `backend/src/application/remember/commands/grade_card.py`

**Intent**: Grading an expired sitting would let one card accumulate showings against a
`showing_limit` the fresh sitting is supposed to start over, and would contradict "a fresh
sitting starts its own per-card showing counts".

**Contract**: `_guard_grade` refuses with `SittingExpiredError` when
`not sitting.is_offered(reviewed_at)`, checked **before** membership, completion and
presentability, and before any write. The single clock read already captured for the event and
the scheduler is the `as_of`.

#### 2. Guard the reads

**File**: `backend/src/application/remember/queries/current_card.py`,
`backend/src/application/remember/queries/reveal_back.py`

**Intent**: An expired sitting must not hand back a card or an `outstanding_count`, or the UI
would present work that cannot be completed.

**Contract**: Both handlers raise `SittingExpiredError` when
`not sitting.is_offered(self._clock.now())`, immediately after the existing
`SittingNotFoundError` check and before any catalog read.

### Success Criteria:

#### Automated Verification:
- `cd backend && uv run pytest tests/bdd -m "remember-flow and (AC-12 or AC-13)"` green
- `cd backend && uv run pytest tests/bdd -m "remember-flow"` green
- `cd backend && uv run pytest` green
- `cd backend && uv run pyright` clean

#### Manual Verification:
- `cd backend && SITTING_RESUME_HORIZON_HOURS=0.001 uv run fastapi dev src/main.py`, then
  `POST /review-sittings`, wait ~5s, and confirm `GET .../current-card`,
  `GET .../cards/{id}/back` and `POST .../cards/{id}/grade` on the stale id each return
  `409 {"code": "sitting_expired"}`, while a second `POST /review-sittings` returns
  `"kind": "opened"` with a different `sitting_id`

---

## Phase 6: TUI API client stubs

### Overview

Materialize the client-side types for the resumed discriminator, the outstanding count, and the
expiry code.

### Changes Required:

#### 1. Regenerate the OpenAPI schema

**File**: `tui/src/api/generated/schema.d.ts`

**Intent**: `outstanding_count` and `SittingResumedDTO` landed on the backend after this file was
last generated.

**Contract**: Regenerated via `pnpm generate:api` against a running backend. No hand edits.

#### 2. Client types and the expiry code

**File**: `tui/src/api/sittings.ts`

**Intent**: Give the store a discriminated result to switch on and a named constant instead of a
stringly-typed comparison.

**Contract**: Exported `SITTING_EXPIRED = "sitting_expired"`. `OpenedSitting` gains
`outstandingCount: number`; a sibling `ResumedSitting` carries the same fields with
`kind: "resumed"`. `openSitting` returns `Promise<OpenedSitting | ResumedSitting | NothingDue>`.
`GradeApplied` gains `outstandingCount: number`. Bodies keep their existing mapping behaviour;
new fields are threaded but not yet asserted.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck` clean
- `cd tui && pnpm lint` clean

#### Manual Verification:
- `cd backend && uv run fastapi dev src/main.py`, then `cd tui && pnpm generate:api`, and confirm
  `git diff src/api/generated/schema.d.ts` shows the `/review-sittings` paths carrying
  `outstanding_count` and a `resumed` variant

---

## Phase 7: TUI API client behaviour

### Overview

Map the new response shapes, and let the expiry code reach the store intact.

### Changes Required:

#### 1. Map the resumed variant and the count

**File**: `tui/src/api/sittings.ts`

**Intent**: The existing `openSitting` rejects anything that is not `opened`, so a resumed
response would currently throw "Unexpected open sitting response".

**Contract**: `openSitting` accepts `opened` and `resumed`, returning the matching `kind` and
mapping `outstanding_count` → `outstandingCount`; the incomplete-response guard
(`card_id == null && !sitting_complete`) applies to both. `gradeCard` maps `outstanding_count`
→ `outstandingCount`. `throwOnClientError` is unchanged — `sitting_expired` already arrives as a
`SittingHttpError` carrying its code.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test test/sittings.test.ts` green, covering: a `resumed` body returns
  `kind: "resumed"`; `outstanding_count` maps onto `outstandingCount` for both open and grade; a
  `409 {code: "sitting_expired"}` body throws `SittingHttpError` whose `code` equals
  `SITTING_EXPIRED`
- `cd tui && pnpm typecheck` clean

### Review r2

Artifact: `reviews/2026-09-10-r2-impl-review.md`

- `R2-F2` — Generated `outstanding_count` is cast optional and defaulted to zero
  Fix: a field the generated schema declares required must be read directly off the typed
  payload; do not cast `data` to a looser shape or supply a fallback for it.

---

## Phase 8: TUI store stubs

### Overview

Materialize the state fields the overlay will read.

### Changes Required:

#### 1. Resume, count and notice state

**File**: `tui/src/store/sitting.ts`

**Intent**: The frame requires the user to see both that they are returning and how many cards
remain; the expiry recovery needs somewhere to say what happened.

**Contract**: `SittingState` gains `isResumed: boolean`, `outstandingCount: number`, and
`notice: string | null`, all present in `initialState` (`false`, `0`, `null`). Action signatures
are unchanged. No behaviour in this phase.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm typecheck` clean
- `cd tui && pnpm test test/sittingStore.test.ts` green — the existing `resetStore` helper is
  updated to the widened shape

---

## Phase 9: TUI store behaviour

### Overview

Record the resume marker and the count, and turn `sitting_expired` from an error into a silent
re-open with a one-line explanation.

### Changes Required:

#### 1. Resume marker and live count

**File**: `tui/src/store/sitting.ts`

**Intent**: The marker is an event (you came back), the count is a state (this many left) — each
rendered according to its nature.

**Contract**: `open()` sets `isResumed` from `result.kind === "resumed"` and `outstandingCount`
from the result. `submitGrade()` updates `outstandingCount` from the grade response and clears
`isResumed` to `false` — the first grade after returning ends the marker's life.

#### 2. Expiry recovery

**File**: `tui/src/store/sitting.ts`

**Intent**: Past the horizon the only sensible answer is a fresh sitting, so asking the user to
confirm it would be a question with one option. The server stays the sole authority; the client
performs the gesture the user would perform by hand.

**Contract**: Every `SittingHttpError` catch checks `error.code === SITTING_EXPIRED` first. On a
match the store does **not** enter `phase: "error"`: it clears `sittingId`/`cardId`/`front`/`back`,
sets `notice` to a fixed message stating the previous session expired and that the grade was not
recorded, sets `phase: "opening"`, and awaits `open()`. Recovery runs at most once per failed
action — a `sitting_expired` returned by the recovery `open()` itself falls through to the
ordinary error path rather than looping. `notice` is cleared by the next successful
`submitGrade`. Every other code keeps the existing `sittingHttpErrorState` path.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test test/sittingStore.test.ts` green, covering: a resumed open sets
  `isResumed` and `outstandingCount`; the first grade clears `isResumed` and updates the count; a
  `sitting_expired` from `gradeCard` leaves `phase` out of `"error"`, sets `notice`, and calls
  `openSitting` exactly once; a non-expiry error still lands in `phase: "error"`
- `cd tui && pnpm typecheck` clean

---

## Phase 10: Overlay shows the return, the count, and the expiry

### Overview

Render the three new facts. No stubs phase: `SittingOverlay` gains no new export.

### Changes Required:

#### 1. Render marker, count and notice

**File**: `tui/src/screens/SittingOverlay.tsx`

**Intent**: Close the frame's requirement that a returning user can tell they are returning and
how many cards are still outstanding.

**Contract**: When `isResumed`, a "Resumed" line renders above the card. The footer carries the
outstanding count in every phase that has a sitting, alongside the existing
`TOGGLE_CARD_HINT`. When `notice` is non-null, it renders as a distinct line and does not
replace the card — the user keeps working. Key handling is unchanged; `notice` is not an error
state and offers no retry key.

### Success Criteria:

#### Automated Verification:
- `cd tui && pnpm test test/sittingOverlay.test.tsx` green, covering: a resumed sitting renders
  "Resumed" and the count; a freshly opened sitting renders the count but not "Resumed"; a
  non-null `notice` renders alongside a presented card rather than in place of it
- `cd tui && pnpm test` green
- `cd tui && pnpm typecheck && pnpm lint` clean

#### Manual Verification:
- Run the backend with `SITTING_RESUME_HORIZON_HOURS=24`, open the TUI, type `/remember`, grade
  one card of a multi-card sitting, press ESC, type `/remember` again — confirm "Resumed" shows,
  the count is one lower, and the marker disappears after the next grade
- Repeat with `SITTING_RESUME_HORIZON_HOURS=0.001`: leave the overlay open past the horizon, press
  a grade key, and confirm the overlay recovers into a fresh sitting with the expiry notice rather
  than showing an error screen

### Review r2

Artifact: `reviews/2026-09-10-r2-impl-review.md`

- `R2-F1` — Outstanding count renders only in the presented phase
  Fix: the outstanding count must render whenever the store holds a `sittingId`, not only in the
  `presented` phase; the toggle hint may stay `presented`-only, because it is the hint, not the
  count, that is phase-specific.

---

## Testing Strategy

### Unit Tests:

Domain behaviour for `is_offered` and `outstanding` already exists from the shaping session's
fills; this change adds no new domain primitives. Application-level tests cover the convergent
branch of `OpenSittingCommand` (offered-and-unfinished, offered-but-finished, expired, none
stored) and the three expiry guards.

### Integration Tests:

The acceptance layer (Phase 1) is the primary integration surface, driven through
`InMemoryRememberComposition` with a fake clock. HTTP-level coverage confirms the
`opened | resumed | nothing_due` union serializes with its discriminator and that
`sitting_expired` maps to 409.

### Manual Testing Steps:

Each phase carries its own recipe. The end-to-end pair — resume inside the horizon, recovery past
it — is exercised from the TUI in Phase 10 using `SITTING_RESUME_HORIZON_HOURS` to make the
horizon crossable within a session.

## Performance Considerations

`latest()` is a full scan in the in-memory adapter. The port deliberately does not name an
unexpired filter, so a future SQL adapter is free to index `opened_at` without changing the
contract. The convergent path adds one repository read and, when resuming, one event-store read
to an operation that already performs several — no new N+1 shape.

## Migration Notes

`Sitting.resume_horizon` carries a field default, so sittings already persisted without it
deserialize with `MIN_RESUME_HORIZON`. The store is in-memory and does not survive a restart, so
no data migration exists in practice. `SITTING_RESUME_HORIZON_HOURS` is optional; omitting it
yields the 24-hour default.

## References

- `context/changes/remember-flow-session-resume/frame.md` — boundaries and requirements
- `context/changes/remember-flow-session-resume/discover-contracts-log.md` — the shaping
  decisions this plan implements, including the `by-id-after-expiry` park resolved here
- `context/efforts/remember-flow/roadmap.md` — slice S-02
- `context/efforts/remember-flow/stories.md` — US-05 (AC-10, AC-11), US-06 (AC-12, AC-13)
- `context/foundation/rules/layering.md`, `cqrs-lite.md`, `exceptions.md`, `contract-testing.md`
- Execution state for this plan lives in `todos.md`, sibling of this file.
