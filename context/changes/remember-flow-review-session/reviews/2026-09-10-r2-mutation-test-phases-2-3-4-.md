# Mutation test review r2

ran at 1d7493d

- **change-id**: remember-flow-review-session
- **scope**: phases 2, 3, 4
- **mutate surface**:
  - `backend/src/domain/remember/value_objects.py` (phase 2)
  - `backend/src/domain/remember/scheduling_state.py` (phase 2)
  - `backend/src/domain/remember/sitting.py` (phases 2, 3)
  - `backend/src/domain/remember/ports.py` (phase 4)
- **date**: 2026-09-10

## Specimens

### R2-F1 — WARNING

- **Operator**: ArgumentReplacement
- **Location**: `backend/src/domain/remember/sitting.py:91`
- **Tests still passed**: Survived
- **Mutant**: `_eligible_pool` passes `None` instead of each `card_id` into `_showing_count`, so every unfinished member reports count zero and ties for the minimum.
- **Fix:** When one member has been shown more than another unfinished member, `next_card` must draw only from those at the minimum showing count.

### R2-F2 — WARNING

- **Operator**: StringLiteral / constant replacement
- **Location**: `backend/src/domain/remember/sitting.py:120`
- **Tests still passed**: Survived
- **Mutant**: `_draw_seed` seeds from `str(None)` instead of `str(self.id.value)` (`xǁSittingǁ_draw_seed__mutmut_2`).
- **Fix:** Two sittings with identical card sets and event sequences must not be assumed to draw the same card unless their sitting ids match.

### R2-F3 — WARNING

- **Operator**: Sort-key removal / constant key (`xǁSittingǁ_draw_seed__mutmut_5`, `__mutmut_7`, `__mutmut_9`)
- **Location**: `backend/src/domain/remember/sitting.py:121`
- **Tests still passed**: Survived
- **Mutant**: `_draw_seed` drops the `(reviewed_at, card_id.value, grade, sitting_id.value)` sort key, so events fold into the seed in insertion order.
- **Fix:** Appending a later `reviewed_at` event must change the draw when multiple unfinished cards tie on showing count.

### R2-F4 — WARNING

- **Operator**: StringLiteral
- **Location**: `backend/src/domain/remember/sitting.py:133`
- **Tests still passed**: Survived
- **Mutant**: `_draw_seed` hashes `str(None)` instead of `str(event.card_id.value)` for each event (`xǁSittingǁ_draw_seed__mutmut_11`).
- **Fix:** Each sitting event's own `card_id` must contribute to the draw seed so reviews on different cards diverge.

### R2-F5 — WARNING

- **Operator**: Slice / `int.from_bytes` arity (`xǁSittingǁ_draw_seed__mutmut_20`, `__mutmut_21`)
- **Location**: `backend/src/domain/remember/sitting.py:140`
- **Tests still passed**: Survived
- **Mutant**: `_draw_seed` reads nine digest bytes or calls `int.from_bytes` without the `"big"` endianness argument instead of `int.from_bytes(digest[:8], "big")`.
- **Fix:** The seeded draw must derive from exactly the first eight big-endian bytes of the SHA-256 digest over the joined parts.

## Classified (not triaged)

- **`_draw_seed__mutmut_12`** (`str(event.sitting_id.value)` → `str(None)`) — equivalent on the filtered log: `_sitting_events` already fixes `sitting_id` for every hashed event.
- **`_draw_seed__mutmut_16`** (`"|".join` → `"XX|XX".join`) — unproductive delimiter wrapping; no exercised input distinguishes the joiner without pinning the seed directly.

## Summary

Five specimens queued (R2-F1–R2-F5). Two mutants classified (equivalent / unproductive). Phases 2 and 4 produced no survivors on their surfaces.
