# Property test review r2

ran at e50bc37

- **change-id**: remember-flow-due-count
- **scope**: phase 2
- **oracle-able surface**: `backend/src/domain/remember/due_partition.py`
- **vector**: input-space / boundary
- **engine**: Hypothesis 6 in pytest
- **max_examples**: 100 per property (`@settings(deadline=30_000)`)

## Properties hunted

1. With no sitting, `total` equals `len(due_card_ids(...))` and the entire total sits in `not_yet_seen` with the other buckets at zero.
2. With a sitting, `total` equals the cardinality of `due_card_ids(...) | sitting.outstanding(visible, events)` and the three buckets sum to `total`.
3. Appending review events for a foreign `sitting_id` does not change the partition (same inputs otherwise).
4. `seen_still_owed` and `not_yet_seen` each stay bounded by the outstanding set size when extra grades are stacked on one card.
5. With scheduler states and random sitting events, the due-union total and bucket sum invariants hold (full `_live_and_states` scenario).
6. Each outstanding member is counted exactly once in `not_yet_seen` or `seen_still_owed` via explicit set splits; `ripe_outside_sitting` equals `|total_set − outstanding|`.
7. Grades logged for card ids outside the sitting do not change the partition.

## Specimens

None.

**no new edge found**

## Classified (not triaged)

None.

## Retractions

None.
