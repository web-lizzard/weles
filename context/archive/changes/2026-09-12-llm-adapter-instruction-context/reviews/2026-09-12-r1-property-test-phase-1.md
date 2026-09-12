# Property test review r1

ran at e98e60a

- **change-id**: llm-adapter-instruction-context
- **scope**: phase 1
- **oracle-able surface**:
  - `backend/src/domain/shared/instruction/model.py`
- **properties hunted** (independent oracle):
  1. When a template uses only named placeholders and value keys match exactly, `InstructionBlock.rendered` stores text equal to `str.format` on the same template and values.
  2. `Instruction` constructs iff block names are unique and every required name appears among blocks; otherwise construction raises `ValueError`.
  3. Duplicate block names always raise `ValueError` containing `twice`.
- **Hypothesis**: `max_examples=100` per test, 30s budget (suite finished under budget)
- **date**: 2026-09-12

## Specimens

None.

**no new edge found**

## Classified (not triaged)

- Initial `valid_rendered_inputs` strategy drew literal text containing `{` without a matching placeholder, which made `Formatter().parse` raise before the SUT was exercised. Strategy narrowed to literals without brace characters; not an instruction-model defect.

## Retractions

None.
