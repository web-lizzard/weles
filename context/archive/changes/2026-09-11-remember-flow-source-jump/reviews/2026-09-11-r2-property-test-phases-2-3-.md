# Property test r2 — phases 2, 3

ran at fa83e25

- **change-id**: remember-flow-source-jump
- **scope**: phases 2, 3
- **oracle-able surface**:
  - `backend/src/domain/remember/review_event.py` (phase 2)
  - `backend/src/domain/remember/sitting.py` (phases 2, 3)
  - `backend/src/domain/remember/ports.py` (phase 2)
  - `backend/src/domain/remember/due_partition.py` (phase 2)
  - `backend/src/domain/remember/review_payload.py` (phase 2)
  - `backend/src/domain/remember/value_objects.py` (phase 2)
- **properties hunted** (Hypothesis, `max_examples=100`, `deadline=30_000` per test):
  - `is_accounting` agrees with graded/rejection vs reveal
  - `is_finishing` is true only for GOOD/EASY grades among graded payloads
  - Reveal-only logs never finish a sitting; reveals do not change `next_card`, `outstanding`, or `is_finished` relative to the same accounting log
  - Rejection is finishing and finishes a single-card present set
  - `partition_due` total and outstanding-bucket sum unchanged when only reveal events are appended (empty baseline)
- **committed property**: `backend/tests/property/remember/test_payload_accounting_properties.py`
- **invoke**: `cd backend && uv run pytest tests/property/remember/test_payload_accounting_properties.py -v`

## Specimens

**no new edge found**

## Classified (not triaged)

- Application command modules (`grade_card.py`, `reject_card.py`) excluded from the oracle-able surface per lane rules (not pure domain).

## Retractions

_(none — no prior property-test artifacts with specimens to re-run)_
