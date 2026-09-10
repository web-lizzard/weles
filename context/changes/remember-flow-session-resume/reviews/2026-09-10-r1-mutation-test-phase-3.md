# Mutation test — phase 3

ran at 8c8f512

- **change-id**: remember-flow-session-resume
- **scope**: phase 3
- **date**: 2026-09-10
- **mutate surface**:
  - `backend/src/application/remember/commands/open_sitting.py`

## Specimens

### R1-F1

- **Severity**: CRITICAL
- **Operator**: `operator_name`
- **Location**: `backend/src/application/remember/commands/open_sitting.py:35`
- **Tests still passed**: Survived (initial run)
- **Mutant**: `ResumeHorizon(value=MIN_RESUME_HORIZON)` → `ResumeHorizon(value=None)` in the omitted-`resume_horizon` default
- **Fix:** assert `OpenSittingCommand` with no `resume_horizon` mints a sitting whose `resume_horizon` equals `MIN_RESUME_HORIZON`
- **Branch**: confirmed kill
- **Evidence**: `415cf20` (`test_open_sitting_without_resume_horizon_uses_min_resume_horizon`)
- Queues no triage row.

### R1-F2

- **Severity**: CRITICAL
- **Operator**: `operator_name`
- **Location**: `backend/src/application/remember/commands/open_sitting.py:67`
- **Tests still passed**: Survived (initial run)
- **Mutant**: `front=reviewable.front` → `front=None` on the convergent resume branch
- **Fix:** assert a resumed sitting DTO carries the current card's `front` text
- **Branch**: confirmed kill
- **Evidence**: `415cf20` (`test_a_resumed_sitting_carries_the_current_card_front`)
- Queues no triage row.

### R1-F3

- **Severity**: CRITICAL
- **Operator**: `operator_arg_removal`
- **Location**: `backend/src/application/remember/commands/open_sitting.py:95`
- **Tests still passed**: Survived (initial run)
- **Mutant**: drops `outstanding_count=` from the `SittingOpenedDTO` constructor (DTO default 0 masks the gap)
- **Fix:** assert an opened sitting DTO reports the live outstanding card count when multiple cards are due
- **Branch**: confirmed kill
- **Evidence**: `415cf20` (`test_an_opened_sitting_reports_how_many_cards_remain_outstanding`)
- Queues no triage row.

## Classified (not triaged)

None.
