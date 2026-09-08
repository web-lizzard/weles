# Property test — phase 2

ran at 56b2ca8

- change-id: `distill-flow-card-anchor-jump`
- scope: phase 2
- vector: input-space / boundary
- engine: Hypothesis 6.165.10 inside pytest (`context/foundation/test-stack.md`)
- numRuns: 100
- interruptAfterTimeLimit: 8000ms deadline per example

## Oracle-able surface

- `backend/src/domain/distill/note_format.py` → phase 2
- `backend/src/domain/distill/note_document.py` → phase 2

## Properties hunted

- Offset map: every kept character maps to a strictly increasing raw index that produced it (space maps to whitespace).
- Block split equals the plan's `\n\s*\n` model; blocks are non-empty substrings in order.
- Normalize value matches the plan's regex chain (strip, one leading marker, drop `*_``, collapse whitespace).
- `locate` returns a location iff the normalized quote is a substring of some block's normalized text; first such block wins.
- A literal interior substring of a plain paragraph resolves `exact` with that slice.
- A quote that is only the first emphasized word of a longer block must not mark the remainder of that block.

## Specimens

### R1-F1 — WARNING

- **Property**: Locating a quote that is only the first word of a longer markdown block must not highlight the rest of that block. Leading emphasis around that word is not a reason to degrade to whole-block precision.
- **Shrunk input**: `content = "lead in\n\n**aaa** and aaaaaaaaaaaaaaaa"`, `quote = "aaa"`
- **Replay**: Hypothesis `@reproduce_failure('6.165.10', b'AXica05MTJyQiAYAXYUIRw==')` (engine analogue of fast-check `seed`+`path`)
- **Proposed pin**: `test_locate_keeps_an_exact_span_when_only_the_first_word_is_emphasized` in `backend/tests/unit/distill/test_note_document.py`
- **Evidence:** (proof: 99a75f0)
- **Fix:** The shrunk input must fail the example suite until a locate of `"aaa"` against that content is `exact` and the raw slice does not contain `"aaaaaaaaaaaaaaaa"`, then remain as regression.

The same `index == 0 and start > 0` blanket also degrades an indented later block (`"lead in\n\n aaaaaaaa"` / quote `"aaaaaaaa"`) to `block`. That shrink is the same invariant, not a second id.

## Classified (not triaged)

- Heading / list / blockquote prefix → `block` is already pinned by `test_locate_degrades_a_heading_match_and_reports_the_second_block`; not re-queued.
- Differential regex model, offset-map monotonicity, and first-match soundness held for 100 examples — not findings.
