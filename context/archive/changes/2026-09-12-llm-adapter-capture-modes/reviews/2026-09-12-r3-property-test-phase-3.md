# Property test — phase 3

```
ran at 29bb0a2
```

- **change-id**: llm-adapter-capture-modes
- **scope**: phase 3
- **date**: 2026-09-12
- **vector**: input-space / boundary
- **engine**: Hypothesis 6 inside pytest (`max_examples=100` per property, ~30s lane budget)
- **oracle-able surface**:
  - `backend/src/domain/shared/graph/machine.py` → phase 3

## Properties hunted

1. `available_transitions()` equals guard-filtered outgoing edges mapped to each target state's `description`, for random 3-node graphs with optional flag guards and arbitrary start context.
2. `transition(target)` returns true and updates the aggregate phase iff `target` is in that available set; otherwise returns false and leaves phase unchanged.
3. `get_tools()` equals `current_state.get_tools(context)` for the same random graphs and contexts.

Committed property module: `backend/tests/property/shared/test_graph_machine_properties.py`

## Specimens

None.

**No new edge found.**

## Classified (not triaged)

None.

## Retractions

None.
