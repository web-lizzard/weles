# Implementation review r4

reviewed at 433e323

- **change-id**: remember-flow-review-session
- **scope**: full (started phases 1–15; phase 16 unstarted and skipped)
- **date**: 2026-09-10
- **evidence commit**: cb66884

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | FAIL |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | FAIL |

**Overall: REJECTED** — two CRITICAL findings.

## Findings

### R4-F1 — CRITICAL — Plan Adherence (MISSING) — phase 1

**Location**: `plan.md` Phase 1 → "Changes Required → 2. Step definitions"

**Evidence:** `proof-test`
`backend/tests/bdd/test_remember_step_coverage.py::test_every_remember_flow_step_resolves_under_its_own_keyword`
— red at 433e323. Four phrases used in the remember-flow feature files have no step
definition registered under the keyword they are written with:

```
when  the user reads the current card again
when  the user starts a review again
when  the user has revealed the current card's back
given the user grades the current card as "good"
```

The last two exist in `backend/tests/bdd/steps/remember_review.py` only as `@given`
(line 439) and `@when` (line 485) respectively; pytest-bdd resolves `And` against the
preceding keyword, so neither is reachable from the scenario that uses it. The plan's
Contract for this phase reads "New `@given` / `@when` / `@then` functions only", and its
Manual criterion reads "fails on assertions rather than on collection" — four scenarios
instead die on `pytest_bdd.exceptions.StepDefinitionNotFoundError`.

**Fix:** Every step phrase appearing in `backend/tests/features/remember-flow/*.feature`
must resolve to a step definition registered under the keyword the scenario writes it
under; a phrase reachable as both `Given` and `When` needs both registrations.

### R4-F2 — CRITICAL — Success Criteria — phase 15

**Location**: `plan.md` Phase 15 → "Success Criteria → Automated Verification"

**Evidence:** `command-output`

```
$ cd backend && uv run pytest
5 failed, 376 passed, 1 warning in 20.28s
exit 1
```

Phase 15's rows 15.1–15.3 are recorded done at `e550265`, but the phase's own whole-suite
gate is red. Two further per-phase gates are red at the same SHA:

```
$ cd backend && uv run pytest tests/bdd -m "remember-flow and AC-09" -q   # phase 7
2 failed, 2 passed, 38 deselected — exit 1
$ cd backend && uv run pytest tests/bdd -m "remember-flow and AC-07" -q   # phase 13
1 failed, 41 deselected — exit 1
```

The scoped suites pass: `uv run pytest tests/unit/remember tests/integration` is
105 passed, and `ruff check src tests` / `basedpyright src` are both clean. Every failure
is in `tests/bdd` and traces to R4-F1 and R4-F3.

**Fix:** `cd backend && uv run pytest` must exit zero before phase 15 counts closed; a
phase whose Automated Verification is red is not done regardless of its row state.

### R4-F3 — WARNING — Safety & Quality — phase 1

**Location**: `backend/tests/bdd/steps/remember_review.py:457`

**Evidence:** `proof-test`
`backend/tests/unit/remember/test_sitting.py::test_the_first_front_over_two_cards_ignores_the_sitting_id`
— red at 433e323: fifty sittings opened over the same two-card set with an empty log draw
both cards, because `Sitting._draw_seed` folds `self.id.value` and `Sitting.open` mints a
fresh `SittingId.new()` each time.

The step

```python
@given(parsers.parse('the card "{label}" is the one in front'))
def card_is_the_one_in_front(...):
    assert remember_flow_context.current_card_id == expected.id
```

therefore asserts the outcome of a coin flip. Observed directly: at 433e323,
`test_a_card_finished_in_the_sitting_stays_out_even_when_still_due_by_schedule` passed in
one `pytest tests/bdd -m "remember-flow"` run and failed in the next, with no change to
the tree.

**Fix:** No acceptance step may assert which of several equally-eligible cards the seeded
draw presents. A scenario that needs a named card in front must either reduce the eligible
pool to one card or read the drawn card and name it, never assume it.

### R4-F4 — WARNING — Plan Adherence (DRIFT) — phase 6

**Location**: `backend/src/application/remember/queries/current_card.py:34-35`

**Evidence:** `proof-test`
`backend/tests/unit/remember/test_current_card_query.py::test_a_finished_sitting_reports_completion_through_the_dto`
— red at 433e323 with `domain.remember.exceptions.SittingAlreadyCompleteError`.

The plan's Phase 6 Contract reads: "`handle(sitting_id)` loads the sitting and its events,
intersects membership with the catalog through `visible`, and returns `sitting.next_card(...)`
as a `PresentedCardDTO` with `sitting_complete` from `is_finished`." The shipped handler
instead raises when the draw is empty:

```python
card_id = sitting.next_card(present, sitting_events)
sitting_complete = sitting.is_finished(present, sitting_events)
if card_id is None:
    raise SittingAlreadyCompleteError
```

`sitting_complete` is computed and then discarded on exactly the branch that would set it
true, so the field is dead on `PresentedCardDTO` and on `SittingOpenedDTO`, which inherits
it — no caller can ever observe it as `True`. Over HTTP a reread of a finished sitting
answers 409 rather than a completion payload.

**Fix:** `CurrentCardQuery` must report completion through `PresentedCardDTO.sitting_complete`
as the phase contract states; if a DTO cannot carry a null `card_id`, change the DTO rather
than the reporting channel — a field no code path can set true is not a contract.

### R4-F5 — WARNING — Plan Adherence (DRIFT) — phase 7

**Location**: `backend/src/application/remember/commands/grade_card.py:69-71`

**Evidence:** `citation`

`plan.md:470` — "One UoW saves the event first, then the scheduling state, then commits."
`plan.md:461` (Intent) — "of event and memoized state the event is the one that must not be lost."

`backend/src/application/remember/commands/grade_card.py:69-71`:

```python
async with asyncio.TaskGroup() as tg:
    _ = tg.create_task(uow.review_events.save(event))
    _ = tg.create_task(uow.scheduling_states.save(next_state))
```

A `TaskGroup` schedules both writes concurrently and cancels the sibling on the first
failure, so the ordering the contract makes explicit — and the priority the Intent states
between the two — is not expressed anywhere in the code. Under the in-memory adapters both
saves are effectively synchronous, which is why no test distinguishes the two shapes today;
against an adapter that can fail or block mid-write the ordering is the whole point.

`proof-test skipped: would require new test infrastructure`

**Fix:** The grade write must save the review event before the memoized scheduling state,
in that order, inside one unit-of-work window. Concurrency between the two is not an
optimization the contract permits.

### R4-F6 — OBSERVATION — Scope Discipline — phase 15

**Location**: `backend/tests/integration/conftest.py:1-30`

**Evidence:** `citation`

`plan.md:924` — "**File**: `backend/tests/integration/support/in_memory_remember.py`" —
names where Phase 16 §1 puts the shared remember composition. Phase 15's commit `817e596`
instead grew that composition inside `backend/tests/integration/conftest.py`, which imports
`FsrsScheduler`, `remember_router`, and the four `get_*` providers. Phase 15's own Changes
Required §3 names only `backend/tests/integration/test_remember_routes.py`.

The extra is benign — a fixture module, not production code — but it pre-empts a Phase 16
deliverable in a different location, so Phase 16 must reconcile the two rather than write
`support/in_memory_remember.py` fresh.

## Retractions

*(none — all three proof-tests from this run are red)*

## Summary

Five rows queued (R4-F1, R4-F3 into phase 1; R4-F4 into phase 6; R4-F5 into phase 7;
R4-F2 into phase 15). Zero retractions. One observation (R4-F6), artifact-only.
