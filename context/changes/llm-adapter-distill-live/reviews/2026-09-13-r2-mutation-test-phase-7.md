# Mutation test review r2

```
ran at 7248f34
```

- **change-id**: llm-adapter-distill-live
- **scope**: phase 7
- **date**: 2026-09-13
- **mutate surface**:
  - `backend/src/domain/distill/flow.py`
- **engine**: mutmut 3.7.0; scoped run (`only_mutate` + `tests/unit/distill/test_distill_flow.py`) because full-suite green-verify fails on unrelated BDD distill scenarios (user-ordered run).

## Mutate surface

- `backend/src/domain/distill/flow.py`

## Specimens

### R2-F1

- **Severity**: CRITICAL
- **Operator**: argument → None
- **Location**: `backend/src/domain/distill/flow.py:269`
- **Tests still passed**: Survived (before killing test)
- **Mutant**: `context.record_verdicts(CandidateRound.REPLACEMENT, event.verdicts)` → `context.record_verdicts(None, event.verdicts)` in `_record_replacement_review`
- **Fix**: After `CardsReviewed` in the replacement-review action, the replacement-round candidate must carry the applied verdict (grade and reasoning).
- **Branch**: confirmed kill
- **Evidence**: assertions in `test_regenerating_route_walk_ends_in_merging_via_replacement_review` (`backend/tests/unit/distill/test_distill_flow.py`, tag `R2-F1`); mutant `domain.distill.flow.x__record_replacement_review__mutmut_2` killed on re-run. Evidence commit pending user confirm. Queues no row.

## Classified (not triaged)

Unproductive (`_ = deps` → `_ = None`; `deps` is intentionally unused):

- **record_first_review__mutmut_1** — `backend/src/domain/distill/flow.py:257`
- **record_replacement_review__mutmut_1** — `backend/src/domain/distill/flow.py:267`

No-coverage (`_discard_duplicates` never exercised by the phase-7 test file):

- **discard_duplicates__mutmut_1** — `backend/src/domain/distill/flow.py:276` (`_ = deps` → `_ = None`)
- **discard_duplicates__mutmut_2** — `backend/src/domain/distill/flow.py:278` (`event.groups` → `None`)

## Retractions

None.
