# Property test review r1 — phase 2

ran at ec1d1b1

- **change-id**: capture-flow-tag-dedup
- **scope**: phase 2
- **oracle-able surface**:
  - `backend/src/domain/capture/value_objects.py`
  - `backend/src/domain/capture/vocabulary.py`
- **engine**: Hypothesis 6.x inside pytest (`context/foundation/test-stack.md`)
- **properties hunted**:
  - Cosine similarity is symmetric for equal-dimension embeddings
  - Cosine self-similarity equals exactly `1.0`
  - Cosine result stays in `[-1.0, 1.0]` and is finite
  - Cosine is invariant under positive scaling of both operands
  - `best_match` returns a candidate whose score is at least the threshold
  - `best_match` returns an identical-embedding candidate at threshold `1.0`
- **budget**: `max_examples=300` per property (`deadline=None`)
- **date**: 2026-09-01

## Specimens

### R1-F1 — WARNING

- **Property**: The cosine similarity of an embedding with itself is exactly `1.0`.
- **Shrunk input**: `Embedding(values=(1.0, 1.0))`
- **Replay**: Hypothesis failing case `test_cosine_self_is_exactly_one(emb=Embedding(values=(1.0, 1.0)))`; also reproduces for `(1e+200, 1e+200)` and large-magnitude pairs whose scaled quotient rounds below `1.0`.
- **Proposed pin**:

```python
def test_R1_F1_cosine_self_similarity_is_exactly_one() -> None:
    emb = Embedding(values=(1.0, 1.0))
    assert emb.cosine_similarity(emb).value == 1.0
```

- **Evidence**: proof-test skipped: HEAD on default branch
- **Fix**: `Embedding(values=(1.0, 1.0))` self-comparison must yield `SimilarityScore(value=1.0)`; an identical-embedding candidate must survive `best_match` at threshold `1.0`.

## Classified (not triaged)

- **Dimension-mismatch raises during cross-dimension generation** — illegal input for the cosine contract; hunt properties restricted to equal-dimension pairs.
- **Symmetry, range, scale-invariance** — held for 300 generated equal-dimension pairs.

## Retractions

(none)

## Summary

**1 specimen queued** (WARNING). Max-abs scaling plus divide still yields self-scores such as `0.9999999999999998`, so `best_match` at threshold `1.0` returns `None` for an identical candidate.
