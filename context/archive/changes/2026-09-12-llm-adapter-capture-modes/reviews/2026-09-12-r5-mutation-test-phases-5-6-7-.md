# Mutation test — phases 5, 6, 7

```
ran at 3a0d25a
```

- **change-id**: llm-adapter-capture-modes
- **scope**: phases 5, 6, 7
- **date**: 2026-09-12
- **engine**: mutmut 3.7.0 + pytest (`context/foundation/testing-conventions.md`)
- **mutate surface**:
  - `backend/src/domain/capture/graph.py` → phases 5, 6, 7
  - `backend/src/domain/capture/capture_session.py` → phase 5
  - `backend/src/domain/capture/turn.py` → phases 6, 7
  - `backend/src/domain/capture/ports.py` → phase 6

## Specimens

### R5-F1

- **Severity**: CRITICAL
- **Operator**: conditional boundary (`or` → `and` on bool guard)
- **Location**: `backend/src/domain/capture/graph.py:298`
- **Tests still passed**: Survived (before proof)
- **Mutant**: `domain.capture.graph.x__require_float__mutmut_2` — `isinstance(value, bool) or not isinstance(...)` → `isinstance(value, bool) and not isinstance(...)`, allowing `True`/`False` to coerce to `1.0`/`0.0` coverage
- **Fix:** `assess_coverage` must reject bool `coverage` arguments with `TypeError`
- **Branch**: confirmed kill — evidence test `backend/tests/unit/capture/test_capture_graph.py::test_assess_coverage_rejects_bool_coverage_r5_f1`; mutant killed on targeted `mutmut run`. Evidence commit pending operator confirm (not on default branch).

### R5-F2

- **Severity**: WARNING
- **Operator**: argument replacement (`UTC` → `None` in `datetime.now`)
- **Location**: `backend/src/domain/capture/capture_session.py:44`
- **Tests still passed**: Survived
- **Mutant**: `domain.capture.capture_session.xǁCaptureSessionǁstart__mutmut_11` — `created_at=datetime.now(UTC)` → `datetime.now(None)` (naive local time)
- **Fix:** A capture graph test that uses `CaptureSession.start()` must assert `created_at.tzinfo is UTC` so mutmut’s dependency-selected suite catches naive timestamps (see `test_model.py::test_start_created_at_is_utc`, which already kills this mutant when run)

## Classified (not triaged)

### Equivalent

- **Operator**: assignment (`_ = context` → `_ = None`)
- **Location**: `backend/src/domain/capture/graph.py:349`
- **Mutant**: `domain.capture.graph.x__assess_coverage__mutmut_1`
- **Why**: Handler only reads `arguments`; discarding `context` is unchanged.

- **Operator**: assignment (`_ = context` → `_ = None`)
- **Location**: `backend/src/domain/capture/graph.py:435` (and parallel proposal/signal handlers at 543, 633, 727, 835, 861)
- **Mutant**: `x__propose_session_topic__mutmut_1`, `x__propose_note_topic__mutmut_1`, `x__propose_note_tag__mutmut_1`, `x__propose_note_content__mutmut_1`, `x__signal_drafting_consent__mutmut_1`, `x__request_conversation__mutmut_1`
- **Why**: Same discard-only change on handlers that do not read `context`/`arguments` beyond validation.

- **Operator**: assignment (`_ = event` → `_ = None`)
- **Location**: `backend/src/domain/capture/graph.py:914`, `946`
- **Mutant**: `x__record_drafting_consent__mutmut_1`, `x__record_conversation_request__mutmut_1`
- **Why**: Bodies do not read `event`; binding is unused.

- **Operator**: keyword removal (`note_id=None`, `phase=CapturePhase.CONVERSING`)
- **Location**: `backend/src/domain/capture/capture_session.py:41`, `43`
- **Mutant**: `xǁCaptureSessionǁstart__mutmut_7`, `xǁCaptureSessionǁstart__mutmut_9`
- **Why**: `CaptureSession` field defaults supply the same values.

### Unproductive

- **Operator**: exception message (`TypeError(f"...")` → `TypeError(None)`)
- **Location**: `backend/src/domain/capture/graph.py:263`, `312`
- **Mutant**: `x__require_str__mutmut_3`, `x__require_float__mutmut_4`
- **Why**: No test asserts tool validation error message text.

### No-coverage residue (capture_session)

- **Operator**: various
- **Location**: `backend/src/domain/capture/capture_session.py` (`draft_note`, `approve`, `_close`, …)
- **Why**: mutmut reported `no tests` for methods outside the phase 5–7 behavioural surface; not triaged.
