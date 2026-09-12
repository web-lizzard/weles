# Mutation test review r2

ran at ebadb6d

- **change-id**: llm-adapter-instruction-context
- **scope**: phase 3
- **mutate surface**:
  - `backend/src/domain/capture/instructions.py`
- **engine**: mutmut 3.7.0 + pytest (`context/foundation/testing-conventions.md`)
- **date**: 2026-09-12

## Mutate surface

- `backend/src/domain/capture/instructions.py`

## Specimens

None.

**no new edge found**

## Classified (not triaged)

- **Engine could not execute mutants on this surface.** Green-verify passed (`589 passed`). Scoped runs (`only_mutate` on the phase file; fresh `mutants/` after removing a stale cache that referenced deleted contract tests) generated a copied module with trampoline imports but **zero** trampolined functions: `instructions.py.meta` had empty `exit_code_by_key`, `instructions.py.spans` was `{"version": 1, "spans": {}}`, and `mutmut run` stopped at stats collection with *“could not find any test case for any mutant”*. Direct inspection of `create_mutations` reported 152 CST mutation sites, all with `contained_by_top_level_function is None`, so `combine_mutations_to_source` never emitted `__mutmut_*` entries. This is an engine/oracle-mapping limitation for this file in the current backend layout, not a surviving behavioural mutant; no triage rows.

## Retractions

None.
