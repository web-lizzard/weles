# Property test review r1

ran at e249947

- **change-id**: remember-flow-review-session
- **scope**: phases 2, 3, 4
- **oracle-able surface**:
  - `backend/src/domain/remember/value_objects.py` (phase 2)
  - `backend/src/domain/remember/scheduling_state.py` (phase 2)
  - `backend/src/domain/remember/sitting.py` (phases 2, 3)
  - `backend/src/domain/remember/ports.py` (phase 4)
- **properties hunted**:
  - `visible` is exactly set intersection and never mutates stored membership
  - `card_is_due` is monotonic in `as_of` when stamp matches
  - `next_card` is deterministic and returns a member of `present` when non-`None`
  - foreign sitting events do not change `next_card` or `is_finished`
  - `SchedulingReplay.replay` matches sequential live review
  - `SchedulingReplay.replay` is invariant under event-order permutation
  - `next_card` never returns a finished card
- **numRuns**: 100 per property (`@settings(max_examples=100)`)
- **interruptAfterTimeLimit**: 30s budget per hunt (lane default; session completed under budget)
- **date**: 2026-09-10
- **vector**: input-space / boundary

## Specimens

### R1-F1 — WARNING

- **Property**: Foreign sitting events must not change the card drawn by `next_card` when this sitting's own events are unchanged — the same foreign-event filter applied to `_eligible_pool` and `is_finished` must apply to the draw seed.
- **Shrunk input**:

```python
sitting_id = SittingId(value=UUID("5ab7c383-a883-4fdf-ab28-0d827faaea53"))
card_ids = {
    CardId(value=UUID("6513270e-269e-0d37-f2a7-4de452e6b438")),
    CardId(value=UUID("d23f0824-128b-2f33-0c5c-7fd0a6a3a450")),
}
own_events = one Grade.FORGOT per card at sitting_id
foreign_events = one Grade.GOOD per card at SittingId("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
```

- **Replay**: `hypothesis-seed=0`, path `test_foreign_sitting_events_do_not_change_next_card_or_finish_state` (3-card shrunk example in failure output)
- **Proposed pin**: `test_R1_F1_foreign_sitting_events_must_not_change_the_drawn_next_card` — fixed sitting id and two-card pool where `next_card` flips between `6513270e…` and `d23f0824…` when foreign events are appended
- **Committed property**: `backend/tests/property/remember/test_remember_domain_properties.py::test_foreign_sitting_events_do_not_change_next_card_or_finish_state`
- **Evidence:** `(proof: 340db23)`
- **Fix**: The shrunk two-card example with sitting `5ab7c383-a883-4fdf-ab28-0d827faaea53` must fail the pin until `_draw_seed` / `_seeded_pick` use only this sitting's events, then remain as regression.

## Classified (not triaged)

- **Replay ignores events for other `card_id`s** — property too strong. Phase 4 contract assumes a card-scoped log from `ReviewEventStore.list_by_card`; filtering at the replay fold would duplicate that port boundary.

## Retractions

*(none)*

## Summary

One specimen queued (R1-F1).
