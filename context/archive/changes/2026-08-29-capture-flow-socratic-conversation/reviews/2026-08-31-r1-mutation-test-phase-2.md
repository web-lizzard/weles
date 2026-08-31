# Mutation test review r1

ran at f5e0e23

- **change-id**: capture-flow-socratic-conversation
- **scope**: phase 2
- **engine**: mutmut 3.7.0 + pytest (per `context/foundation/test-stack.md`)
- **date**: 2026-08-31

## Mutate surface

- `backend/src/domain/capture/value_objects.py`
- `backend/src/domain/capture/capture_session.py`
- `backend/src/domain/capture/message.py`

## Specimens

### R1-F1 — CRITICAL

- **Operator**: argument replacement
- **Location**: `backend/src/domain/capture/capture_session.py:21`
- **Tests still passed**: Survived
- **Mutant**: `datetime.now(UTC)` → `datetime.now(None)`
- **Fix:** assert `CaptureSession.start().created_at.tzinfo is UTC`
- **Proof**: killing test `test_start_created_at_is_utc` in `backend/tests/unit/capture/test_model.py` — confirmed kill; `proof-test skipped: HEAD on default branch`

### R1-F2 — CRITICAL

- **Operator**: argument replacement
- **Location**: `backend/src/domain/capture/message.py:32`
- **Tests still passed**: Survived
- **Mutant**: `datetime.now(UTC)` → `datetime.now(None)`
- **Fix:** assert `Message.record(...).created_at.tzinfo is UTC`
- **Proof**: killing test `test_record_created_at_is_utc` in `backend/tests/unit/capture/test_model.py` — confirmed kill; `proof-test skipped: HEAD on default branch`

## Classified (not triaged)

No equivalent or unproductive mutants on the phase 2 surface. `value_objects.py` mutants were all killed by existing tests.
