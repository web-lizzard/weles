# Mutation test review r2

ran at ee230e7

- **change-id**: capture-flow-draft-note
- **scope**: phase 3
- **engine**: mutmut 3.7.0 + pytest (per `context/foundation/test-stack.md`)
- **date**: 2026-09-01

## Mutate surface

- `backend/src/domain/capture/value_objects.py`
- `backend/src/domain/capture/topic.py`
- `backend/src/domain/capture/tag.py`
- `backend/src/domain/capture/note.py`
- `backend/src/domain/capture/capture_session.py`
- `backend/src/adapters/http/errors.py`

## Specimens

### R2-F1 — CRITICAL

- **Operator**: string replacement / argument replacement
- **Location**: `backend/src/adapters/http/errors.py:28`
- **Tests still passed**: Survived
- **Mutant**: `content = {"code": exc.code(), "detail": str(exc)}` → renamed `detail` key (`XXdetailXX`, `DETAIL`) or `str(None)` instead of `str(exc)`
- **Fix:** assert `core_exception_handler` response JSON includes `detail` equal to `str(exc)`
- **Proof**: killing test `test_R2_F1_core_exception_handler_includes_detail_message` in `backend/tests/unit/test_http_error_mapping.py` — confirmed kill on mutants 10–12; `proof-test skipped: HEAD on default branch`

### R2-F2 — WARNING

- **Operator**: argument replacement
- **Location**: `backend/src/adapters/http/errors.py:27`
- **Tests still passed**: Survived
- **Mutant**: `EXCEPTION_STATUS_MAP.get(exc.code(), 500)` → default `None`, empty, or `501`
- **Fix:** assert `core_exception_handler` returns HTTP 500 when `exc.code()` is absent from `EXCEPTION_STATUS_MAP`

## Classified (not triaged)

- **`CaptureSession.start()` omits explicit `note_id=None`** (`backend/src/domain/capture/capture_session.py:34`) — equivalent: `note_id` already defaults to `None` on the model field; removing the explicit keyword does not change observable behaviour.
