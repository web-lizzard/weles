# Mutation test — phase 3

```
ran at 29bb0a2
```

- **change-id**: llm-adapter-capture-modes
- **scope**: phase 3
- **date**: 2026-09-12
- **engine**: mutmut 3.7.0 + pytest (`context/foundation/testing-conventions.md`)
- **mutate surface**:
  - `backend/src/domain/shared/graph/machine.py` → phase 3

## Specimens

None.

## Classified (not triaged)

### Equivalent

- **Operator**: argument replacement (`self._context` → `None` in delegate call)
- **Location**: `backend/src/domain/shared/graph/machine.py:46`
- **Mutant**: `domain.shared.graph.machine.xǁStateMachineǁget_tools__mutmut_1`
- **Why**: `get_tools()` still returns the current state's tool sequence; the exercised states expose fixed `tools` and default `State.get_tools` discards `context`, so `None` is observably the same.

- **Operator**: argument replacement (`self._context` → `None` in `get_actions` call)
- **Location**: `backend/src/domain/shared/graph/machine.py:54`
- **Mutant**: `domain.shared.graph.machine.xǁStateMachineǁapply__mutmut_1`
- **Why**: The apply test's stamping state selects actions from `event` only; rebinding `context` to `None` does not change which actions run.

- **Operator**: argument replacement (`self._context` → `None` in action invocation)
- **Location**: `backend/src/domain/shared/graph/machine.py:55`
- **Mutant**: `domain.shared.graph.machine.xǁStateMachineǁapply__mutmut_5`
- **Why**: The invoked state action in the apply test ignores its context parameter; passing `None` leaves the side effect unchanged.

- **Operator**: argument replacement (`event` → `None` in action invocation)
- **Location**: `backend/src/domain/shared/graph/machine.py:55`
- **Mutant**: `domain.shared.graph.machine.xǁStateMachineǁapply__mutmut_6`
- **Why**: The invoked state action ignores its event parameter; passing `None` leaves the side effect unchanged.

- **Operator**: argument replacement (`self._context` → `None` in edge action invocation)
- **Location**: `backend/src/domain/shared/graph/machine.py:88`
- **Mutant**: `domain.shared.graph.machine.xǁStateMachineǁtransition__mutmut_6`
- **Why**: The transition test's edge action ignores its context parameter; passing `None` still records the same invocation and phase write.
