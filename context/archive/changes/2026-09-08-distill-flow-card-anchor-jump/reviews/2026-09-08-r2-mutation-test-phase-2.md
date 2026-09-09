# Mutation test — phase 2

ran at 901c01d

- change-id: `distill-flow-card-anchor-jump`
- scope: phase 2
- engine: mutmut 3.7.0 + pytest (`context/foundation/test-stack.md`)
- mutate surface:
  - `backend/src/domain/distill/note_format.py` → phase 2
  - `backend/src/domain/distill/note_document.py` → phase 2

## Specimens

### R2-F1 — WARNING

- **Operator**: NumberIncrement / comparison on `_after_leading_marker` (mutmut `x__after_leading_marker__mutmut_9` and the whole `text[start].isdigit()` cluster `__mutmut_15`–`32`)
- **Location**: `backend/src/domain/distill/note_format.py:70`
- **Tests still passed**: Survived
- **Mutant**: The suite only exercises a single `# ` heading. Mutants that skip a second `#`, ignore `1.` / `1)`, treat `.)` as non-markers, or rewrite the digit loop all stayed green because those prefixes never appear in tests.
- **Fix:** Normalizing a block drops exactly one leading run matching `^(?:[#>+-]+|\d+[.)])\s*` (including `## Title`, `> quote`, `- item`, and `1. item`) and keeps the remainder as comparable text.

### R2-F2 — WARNING

- **Operator**: StringLiteral (`strip` charset)
- **Location**: `backend/src/domain/distill/note_format.py:22`
- **Tests still passed**: Survived
- **Mutant**: `block.strip("\n")` → `block.strip(None)` (`MarkdownNoteFormat.blocks__mutmut_1`)
- **Fix:** After splitting on blank lines, a kept block retains leading and trailing spaces; only surrounding newlines are stripped.

### R2-F3 — WARNING

- **Operator**: NumberIncrement / comparison on `_trimmed_bounds`
- **Location**: `backend/src/domain/distill/note_format.py:60`
- **Tests still passed**: Survived
- **Mutant**: Leading/trailing trim loops never run on the current examples, so `start += 1` → `= 1` / `+= 2` / `-= 1` and `end -= 1` → `= 1` / `+= 1` / `-= 2` (`x__trimmed_bounds__mutmut_5`–`15`) all survived.
- **Fix:** `normalize` omits leading and trailing whitespace from `value` and from `offsets`; a quote padded with spaces still matches the unpadded block.

### R2-F4 — WARNING

- **Operator**: Name (`str.find` → `str.rfind`)
- **Location**: `backend/src/domain/distill/note_document.py:63`
- **Tests still passed**: Survived
- **Mutant**: `normalized.value.find(quote.value)` → `rfind` (`x__locate_in_block__mutmut_5`)
- **Fix:** When the normalized quote occurs more than once in a block, `locate` marks the first span, not the last.

### R2-F5 — WARNING

- **Operator**: NumberIncrement
- **Location**: `backend/src/domain/distill/note_document.py:68`
- **Tests still passed**: Survived
- **Mutant**: `end = normalized.offsets[last] + 1` → `+ 2` (`x__locate_in_block__mutmut_16`)
- **Fix:** An `exact` location's `end` is exclusive of the raw character after the last kept quote character (`offsets[last] + 1`), so a following letter is not swept into the span and must not force `block` precision.

## Classified (not triaged)

- `MarkdownNoteFormat.blocks__mutmut_2` (`strip("\n")` → `strip("XX\nXX")`) — unproductive string wrapping; still strips newline.
- `x__after_leading_marker__mutmut_1` (`start >= end` → `>`), `__mutmut_5` / `__mutmut_11` (`<` → `<=` on marker/space loops) — equivalent on the tested `# TCP Handshake` input (the cursor never lands on `end`).
- `x__after_leading_marker__mutmut_7` (`cursor += 1` → `= 1`) — equivalent for a single `# ` marker; covered by R2-F1 for `##`.
- Numbered-list mutants `__mutmut_15`–`32` — same missing oracle as R2-F1; not separate ids.
- Trim-loop mutants besides the R2-F3 representative — same missing oracle as R2-F3.
- `x__has_structural_prefix__mutmut_8` (`leading_ws + marker.end()` → `-`) — equivalent: any match in a marked block already has `start` at or after the marker, so both comparisons degrade to `block`.
- Timeouts (not specimens): `normalize__mutmut_16`, `17`, `21`, `22`, `32`, `33`; `x__after_leading_marker__mutmut_12`.

R1-F1 (leading emphasis marking the rest of the paragraph) is already `[x]` and is a different invariant; not re-queued.
