# Mutation test — phase 1

```
ran at a029017
```

- **change-id**: llm-adapter-capture-modes
- **scope**: phase 1
- **engine**: mutmut 3.7.0 + pytest (`context/foundation/testing-conventions.md`)
- **mutate surface**:
  - `backend/src/domain/shared/graph/model.py` → phase 1

## Specimens

None.

## Classified (not triaged)

### Equivalent

- **Operator**: assignment (`_ = context` → `_ = None`)
- **Location**: `backend/src/domain/shared/graph/model.py:108`
- **Mutant**: `domain.shared.graph.model.xǁStateǁget_tools__mutmut_1`
- **Why**: Default `get_tools` still returns `self.tools`; rebinding the discard to `None` does not change observable behaviour.

- **Operator**: assignment (`_ = context, event` → `_ = None`)
- **Location**: `backend/src/domain/shared/graph/model.py:118`
- **Mutant**: `domain.shared.graph.model.xǁStateǁget_actions__mutmut_1`
- **Why**: Default `get_actions` still returns `self.actions`; same discard-only change.

### Timeout (not a specimen)

- **Operator**: assignment (`name = frontier.pop()` → `name = None`)
- **Location**: `backend/src/domain/shared/graph/model.py:209`
- **Mutant**: `domain.shared.graph.model.xǁGraphǁreachable_from__mutmut_5`
- **Why**: Breaks BFS termination; mutmut reported timeout, not survival.
