# Impl review — full plan

reviewed at 50ecce4

| Field | Value |
| --- | --- |
| change-id | distill-flow-grounded-generation |
| scope | full |
| date | 2026-09-05 |

## Verdicts

| Dimension | Verdict |
| --- | --- |
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

**Overall: APPROVED**

## Findings

### R3-F2 — `test_note_document_parser.py` duplicates the contract suite against the concrete adapter

- **Severity**: WARNING
- **Dimension**: Pattern Consistency
- **Location**: `backend/tests/unit/distill/test_note_document_parser.py:1-25`
- **Evidence**: `citation` — the file imports `MarkdownNoteDocumentParser` directly and hardcodes it:

  ```python
  from adapters.out.in_memory.distill.note_document_parser import (
      MarkdownNoteDocumentParser,
  )
  ...
  async def test_leading_block_markers_strip_before_matching() -> None:
      parser = MarkdownNoteDocumentParser()
  ```

  duplicating the same two invariants already pinned, parametrized over `_IMPLEMENTATIONS`, in `backend/tests/unit/distill/contracts/test_note_document_parser_contract.py:29-46` (cases `"heading-text-without-its-marker"`, `"reflowed-across-a-line-wrap"`). Two agreeing siblings establish the project's actual pattern: `backend/tests/unit/capture/contracts/test_reply_generation_contract.py` and `backend/tests/unit/capture/contracts/test_topic_extraction_contract.py` — capture's deterministic in-memory adapters each get exactly one contract-parametrized suite under `contracts/`, with no sibling concrete-adapter test file at `tests/unit/capture/`'s top level. `context/foundation/rules/contract-testing.md`: "Each port has one behavioral contract-test suite, parametrized over its adapter implementations."
- **Fix:** a deterministic in-memory adapter gets exactly one contract-parametrized suite under `contracts/`; a normalization invariant belongs there, parametrized over `_IMPLEMENTATIONS`, not in a standalone concrete-class test file — a future second `NoteDocumentParser` adapter would silently skip this file's two cases.

### R3-F3 — `test_note_document_parser.py` is not named in any phase's Changes Required

- **Severity**: WARNING
- **Dimension**: Scope Discipline
- **Location**: `backend/tests/unit/distill/test_note_document_parser.py` (whole file, added in `f86e8af`)
- **Evidence**: `citation` — Phase 8's Changes Required (`context/changes/distill-flow-grounded-generation/plan.md:426-432`) names only:

  > **File**: `backend/tests/unit/distill/contracts/test_note_document_parser_contract.py`
  > **Contract**: Covers verbatim resolution; resolution across differing line wrapping; resolution through `**bold**` and `` `code` `` markers; a heading's text resolving without its `#`; non-resolution of a fabricated quote; non-resolution of a cross-block quote; non-resolution of an empty and a whitespace-only quote.

  No phase across the plan's 14 phases names `test_note_document_parser.py`. `git diff --stat 1f0e699..HEAD` confirms it as a net-new file outside the enumerated file set.
- **Fix:** test coverage added to satisfy a Review-triage fix belongs in the plan-named contract file; do not create a new file outside any phase's Changes Required.

## Retractions

- **R3-F1** — Plan Adherence MISSING, Phase 11: `GenerateCardsCommand`'s Contract (`plan.md:560`) names seven test outcomes; two — a missing note reaching the logged no-op, and a structurally invalid proposal being skipped while its siblings survive — had no corresponding test in `backend/tests/unit/distill/test_generate_cards_command.py`. Proof-tests `test_generate_cards_missing_note_is_a_logged_no_op` and `test_generate_cards_skips_a_structurally_invalid_proposal_while_siblings_survive`, written by this review into that file, both pass against `backend/src/application/distill/commands/generate_cards.py:34-36` (missing-note no-op) and `:65-69` (per-proposal `except CoreException: ... continue`) at `50ecce4` — not reproduced. The two behaviors are correctly implemented; only their test coverage was missing. The tests remain in the working tree, uncommitted per the default-branch guardrail.
- **R3-F4** — Plan Adherence MISSING, Phase 4 Review r2: the fix for `R2-F3`/`R2-F4` (assert `created_at`/`discarded_at` carry `tzinfo is UTC`) is recorded `[x]` at `todos.md` rows 4.6/4.7, but `git log --follow -- backend/tests/unit/distill/test_card_factory.py` shows no commit past `9bb6105` (the original Phase 4 test-authoring commit) — the assertions exist only as an unstaged working-tree diff, never committed. Running `test_card_factory.py` as it stands (including that uncommitted diff) against `backend/src/domain/distill/card_factory.py:34,58` at `50ecce4` — not reproduced: `datetime.now(UTC)` is used on both the live-mint and oversized-discard paths, so the invariant holds. The defect is a committed-evidence gap, not a behavioral one: **the fix itself was never committed and remains an unstaged diff in the working tree.**
