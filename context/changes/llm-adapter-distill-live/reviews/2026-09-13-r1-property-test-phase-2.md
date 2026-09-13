# Property test review r1

```
ran at 7d51c1b
```

| Field | Value |
| --- | --- |
| change-id | `llm-adapter-distill-live` |
| scope | phase 2 |
| date | 2026-09-13 |
| vector | input-space / boundary |
| numRuns | `max_examples=100` per property (Hypothesis); no `interruptAfterTimeLimit` (completed under 30s budget) |

## Oracle-able surface

- `backend/src/domain/distill/regeneration.py` (phase 2)
- `backend/src/domain/distill/value_objects.py` (phase 2 — `ReviewGrade` only)

## Properties hunted

1. **`RegenerationPolicy.regenerate`** — for valid ascending tier lists ending open, result equals the contract oracle: first tier whose ceiling covers note length, then `proposed == 0` or `accepted / proposed < min_accepted_share`.
2. **`ReviewGrade.rank`** — equals zero-based declaration index (POOR lowest).
3. **`ReviewGrade.passes`** — true only for `SOUND` and `STRONG`.
4. **`RegenerationPolicy` construction** — raises `ValueError` iff a reference model rejects the tier list (empty, non-ascending finite ceilings, open tier not last, multiple open tiers).

Session file (not evidence commit — no specimens): `backend/tests/property/distill/test_regeneration_policy_properties.py`

## Specimens

**no new edge found**

## Classified (not triaged)

None.

## Retractions

None.
