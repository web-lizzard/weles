# Property test — phase 1

```
ran at a029017
```

- **change-id**: llm-adapter-capture-modes
- **scope**: phase 1
- **date**: 2026-09-12
- **vector**: input-space / boundary
- **engine**: Hypothesis 6 inside pytest (`max_examples=100` per property, ~30s budget lane default)
- **oracle-able surface**:
  - `backend/src/domain/shared/graph/model.py`

## Properties hunted

1. `reachable_from(source)` equals independent BFS over the declared transition adjacency (guards ignored), for every source on random 4-node graphs without self-loops.
2. `terminal_states` and `is_terminal` match the set of declared states with no outgoing edge in `transitions`.
3. Every state in `reachable_from(source)` is a key of `states`.

## Specimens

None.

**No new edge found.**

## Classified (not triaged)

None.

## Retractions

None.
