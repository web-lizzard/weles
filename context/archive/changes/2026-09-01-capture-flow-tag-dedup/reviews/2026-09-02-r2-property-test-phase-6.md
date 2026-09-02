# Property test review r2 — phase 6

ran at 7a6717b

- **change-id**: capture-flow-tag-dedup
- **scope**: phase 6
- **oracle-able surface**:
  - `backend/src/application/capture/services/vocabulary.py`
- **engine**: Hypothesis 6.x inside pytest (`context/foundation/test-stack.md`)
- **properties hunted**:
  - Double-resolve of the same canonical label is idempotent (`reused=True`, same id, store size unchanged)
  - `reused` flag matches store growth (reuse leaves size; mint grows by one)
  - When `best_match` would hit, resolver returns the stored row's label, not the query label
  - Whitespace-padded labels reuse the canonical stripped entry
  - Mint count after a label sequence equals the oracle cluster count (no false merges or misses)
  - Stored label is not mutated on reuse
  - Sequential identical labels never grow the store beyond one row
  - Pre-seeded identical-embedding candidates at threshold 1.0 reuse the older `created_at` tie-break winner
  - Brute-force scan of 2000 distinct labels found zero cross-label pairs at or above threshold 0.85
- **budget**: `max_examples=300` per property (`deadline=None`); brute-force scan over 2000 labels
- **date**: 2026-09-02

## Specimens

(none)

## Classified (not triaged)

- **Whitespace-only or strip-to-empty labels** — `Label` raises `EmptyLabelError` before the resolver runs; illegal input for this surface.
- **All-zero synthetic embeddings in tie-break harness** — `ZeroMagnitudeEmbeddingError` from the cosine metric; illegal input, not a resolver defect.
- **Idempotence, store-growth coupling, stored-label invariant, tie-break with fixed embed port** — held for the generated budgets.

## Retractions

(none)

## Summary

**No new edge found.** Phase 6 reuse-or-mint behavior on `VocabularyResolver` matches the reference oracle across 300 generated label sequences per property; no cross-label hash collision surfaced in a 2000-label brute-force scan at threshold 0.85.
