# Mutation test review r2

- **change-id**: remember-flow-card-rejection
- **scope**: phase 2
- **date**: 2026-09-11
- **ran at** f4fb33a

## Mutate surface

- `backend/src/domain/remember/sitting.py`
- `backend/src/domain/remember/ports.py` (`SchedulingReplay.replay`)

## Specimens

### R2-F1

- **Severity**: CRITICAL
- **Operator**: continue → break
- **Location**: `backend/src/domain/remember/ports.py:97`
- **Tests still passed**: Survived (before killing test)
- **Mutant**: `if event.card_id != card_id: continue` → `break`
- **Fix**: After a foreign `card_id`, `SchedulingReplay.replay` must still fold later graded events for the requested card (continue, never break).
- **Branch**: confirmed kill
- **Evidence**: killing test `test_replay_skips_foreign_cards_without_stopping_on_later_target_grades` in `backend/tests/unit/remember/test_scheduling_replay.py`; mutant `domain.remember.ports.xǁSchedulingReplayǁreplay__mutmut_3` killed on re-run.

### R2-F2

- **Severity**: WARNING
- **Operator**: string replacement
- **Location**: `backend/src/domain/remember/sitting.py:184`
- **Tests still passed**: Survived
- **Mutant**: `str(event.sitting_id.value)` → `str(None)` in `_draw_seed` event parts
- **Fix**: `_draw_seed` must include each event's real `sitting_id` in the hash input so `next_card` picks change when sitting identity in the log changes.

### R2-F3

- **Severity**: WARNING
- **Operator**: slice index
- **Location**: `backend/src/domain/remember/sitting.py:188`
- **Tests still passed**: Survived
- **Mutant**: `digest[:8]` → `digest[:9]` in `int.from_bytes`
- **Fix**: Draw seed must use exactly the first eight SHA-256 digest bytes (big-endian), not nine.

### R2-F4

- **Severity**: WARNING
- **Operator**: comparison operator
- **Location**: `backend/src/domain/remember/sitting.py:106`
- **Tests still passed**: Survived
- **Mutant**: `as_of < opened_at + horizon` → `<=`
- **Fix**: `is_offered` must be false at exactly `opened_at + resume_horizon` (strict `<`, not inclusive).

## Classified (not triaged)

- **draw_seed mutmut_20** (`backend/src/domain/remember/sitting.py:188`, byteorder operand removed): unproductive — exercised `next_card` scenarios do not distinguish this arid `int.from_bytes` operand mutation from the canonical seed.
