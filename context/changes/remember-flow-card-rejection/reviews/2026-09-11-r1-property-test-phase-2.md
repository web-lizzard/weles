# Property test review r1

- **change-id**: remember-flow-card-rejection
- **scope**: phase 2
- **date**: 2026-09-11
- **ran at** de6d49c
- **vector**: input-space / boundary (Hypothesis 6 in pytest)
- **numRuns**: 100 (`max_examples` per property)
- **interruptAfterTimeLimit**: not used (suite completed under 30s budget)

## Oracle-able surface

- `backend/src/domain/remember/sitting.py`
- `backend/src/domain/remember/ports.py` (`SchedulingReplay`)

## Properties hunted

1. A rejected card never appears in `outstanding`.
2. `next_card` never returns a card already finished (including via `Rejected`).
3. A rejection-only log replays to `None`.
4. Mixed logs replay identically to the grades-only oracle.
5. `replay(card_a, events)` is invariant when foreign-card grades are present vs scoped to `card_a` only.

## Specimens

### WARNING

- **Property**: Rebuilding scheduling state for one card must fold only that card's graded events; another card's grades in the same sequence must not change the result.
- **Shrunk input**:
  - `card_a` = `e3e70682-c209-4cac-629f-6fbed82c07cd`
  - `card_b` = `f728b4fa-4248-5e3a-0a5d-2f346baa9455`
  - `grade_a` = `forgot`, `grade_b` = `forgot`
  - `reviewed_at` = `2026-08-01T00:00:00+00:00` and `2026-08-01T01:00:00+00:00`
- **Replay**: Hypothesis `@example` on `test_replay_ignores_grades_belonging_to_other_cards` (explicit example after shrink); hunt `max_examples=100`.
- **Proposed pin**: `test_replay_for_one_card_ignores_another_cards_grades_in_the_sequence` in `backend/tests/unit/remember/test_scheduling_replay.py` (unit regression; hunt was Hypothesis, pin lives with other replay tests)
- **Committed property**: `test_replay_ignores_grades_belonging_to_other_cards` in `backend/tests/property/remember/test_remember_domain_properties.py` (`@example` carries the shrunk vector; `@given` keeps hunting); run `cd backend && uv run pytest tests/property/remember/test_remember_domain_properties.py -k replay_ignores_grades -v`
- **Fix**: The shrunk two-card log must make `SchedulingReplay.replay(card_a, events)` equal `replay(card_a, events)` with only `card_a` events until the bug is fixed; the unit pin and this property stay as regression afterward.
- **Evidence:** `(proof: 3f99e12)`

## Classified (not triaged)

- Rejection settlement and mixed-log replay properties: held for all generated cases (no counterexample).

## Retractions

(none)
