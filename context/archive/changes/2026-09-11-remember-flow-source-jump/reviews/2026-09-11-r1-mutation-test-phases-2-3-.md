# Mutation test r1 — phases 2, 3

ran at c53d26a

- **change-id**: remember-flow-source-jump
- **scope**: phases 2, 3
- **mutate surface**:
  - `backend/src/domain/remember/review_event.py`
  - `backend/src/domain/remember/sitting.py`
  - `backend/src/domain/remember/ports.py`
  - `backend/src/domain/remember/due_partition.py`
  - `backend/src/application/remember/commands/grade_card.py`
  - `backend/src/application/remember/commands/reject_card.py`
  - `backend/src/domain/remember/review_payload.py`
  - `backend/src/domain/remember/value_objects.py`

## Specimens

### R1-F1 — CRITICAL — confirmed kill

- **Operator**: mutmut boolean replacement
- **Location**: `backend/src/domain/remember/review_payload.py:23`
- **Tests still passed**: Survived (full run; targeted rerun killed after evidence test)
- **Mutant**: `return True` → `return False` for `Rejection` in `is_finishing`
- **Fix:** assert `is_finishing(Rejection())` is true
- **Branch**: confirmed kill
- **Evidence**: `tests/unit/remember/test_sitting.py::test_is_finishing_treats_a_rejection_as_finishing` (pending evidence commit)

### R1-F2 — CRITICAL — confirmed kill

- **Operator**: mutmut string replacement
- **Location**: `backend/src/domain/remember/sitting.py:180`
- **Tests still passed**: Survived
- **Mutant**: `"rejected"` → `"XXrejectedXX"` / `"REJECTED"` in `_draw_seed`
- **Fix:** draw-seed hashing must use the literal token `rejected` for `Rejection` payloads
- **Branch**: confirmed kill
- **Evidence**: `tests/unit/remember/test_sitting.py::test_draw_seed_maps_a_rejection_to_the_rejected_literal` (pending evidence commit)

### R1-F5 — CRITICAL — confirmed kill

- **Operator**: mutmut comparison operator replacement
- **Location**: `backend/src/domain/remember/sitting.py:108`
- **Tests still passed**: Survived
- **Mutant**: `<` → `<=` in `is_offered`
- **Fix:** `is_offered` is false exactly at `opened_at + resume_horizon` (strict `<`)
- **Branch**: confirmed kill
- **Evidence**: existing `test_is_offered_is_false_at_opened_at_plus_resume_horizon` (docstring tagged R1-F5)

### R1-F6 — CRITICAL — confirmed kill

- **Operator**: mutmut assignment
- **Location**: `backend/src/application/remember/commands/grade_card.py:62`
- **Tests still passed**: Survived
- **Mutant**: `updated_states[card_id] = next_state` → `None`
- **Fix:** `handle` must persist `scheduler.review()` output to `scheduling_states`
- **Branch**: confirmed kill
- **Evidence**: `tests/unit/remember/test_grade_card_command.py::test_grading_persists_the_scheduler_review_output_as_memoized_state` (pending evidence commit)

### R1-F7 — WARNING

- **Operator**: mutmut assignment
- **Location**: `backend/src/application/remember/commands/grade_card.py:71`
- **Tests still passed**: Survived
- **Mutant**: `self._scheduler.stamp()` → `None` passed to `partition_due`
- **Fix:** `partition_due` must receive the live `Scheduler.stamp()` from `GradeCardCommand.handle`

### R1-F8 — WARNING

- **Operator**: mutmut argument deletion
- **Location**: `backend/src/application/remember/commands/grade_card.py:123`
- **Tests still passed**: Survived
- **Mutant**: drops `outstanding_count=` when `sitting_complete=True`
- **Fix:** complete `GradeAppliedDTO` includes `outstanding_count`

### R1-F9 — WARNING

- **Operator**: mutmut argument deletion
- **Location**: `backend/src/application/remember/commands/grade_card.py:126`
- **Tests still passed**: Survived
- **Mutant**: drops `due=` on complete DTO branch
- **Fix:** complete `GradeAppliedDTO` includes `due`

### R1-F10 — WARNING

- **Operator**: mutmut assignment
- **Location**: `backend/src/application/remember/commands/grade_card.py:136`
- **Tests still passed**: Survived
- **Mutant**: `next_front=next_card.front` → `None`
- **Fix:** incomplete `GradeAppliedDTO` carries the next card front text

### R1-F11 — WARNING

- **Operator**: mutmut argument deletion
- **Location**: `backend/src/application/remember/commands/grade_card.py:134`
- **Tests still passed**: Survived
- **Mutant**: drops `outstanding_count=` on incomplete branch
- **Fix:** incomplete `GradeAppliedDTO` includes `outstanding_count`

## Classified (not triaged)

- `domain.remember.sitting.xǁSittingǁ_draw_seed__mutmut_9` — duplicate oracle of R1-F2 (rejection token casing)
- `domain.remember.sitting.xǁSittingǁ_draw_seed__mutmut_22` — covered by `test_draw_seed_includes_event_sitting_id_in_hash_input` (mutmut cache lag on full run)
- `domain.remember.sitting.xǁSittingǁ_draw_seed__mutmut_30` — unproductive (`int.from_bytes` arity breakage)
- `domain.remember.sitting.xǁSittingǁ_draw_seed__mutmut_31` — covered by `test_draw_seed_uses_exactly_eight_digest_bytes_big_endian`
- `application.remember.commands.grade_card.xǁGradeCardCommandǁ_applied_dto__mutmut_15` — unproductive (breaks `GradeAppliedDTO` construction syntax)
