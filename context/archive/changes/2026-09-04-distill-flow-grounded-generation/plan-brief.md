# Grounded Flashcard Generation — Plan Brief

> Full plan: `plan.md`

## What & Why

A note approved in capture already lands in distill and enqueues `note_saved` — which nothing consumes. This slice (`distill-flow` S-02, AC-03–AC-06) builds the entire card side of the domain and the handler that consumes that envelope, so flashcards come into existence with no user action, every live card quotes its note verbatim, and a note yielding zero live cards is reported as completed rather than failed.

## Starting Point

`domain/distill/` holds only the `Note` aggregate, its value objects, a `NoteRepository`, and the `note_saved` envelope; `application/distill/` holds `SaveNoteCommand` and a `UnitOfWork` over notes and outbox. Nothing card-shaped exists. `compose.py` registers `SaveNoteHandler` as the only outbox handler.

## Desired End State

Approving a note produces live cards each carrying a resolvable verbatim quote, plus persisted discarded rows for every proposal that failed grounding or breached the length policy. `distillation_status` reaches `ready` whether the note produced ten live cards or none, and `failed` only when the generation port itself fails.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Quote-matching rule | Normalized single-block substring: collapse whitespace, strip inline emphasis and block markers, exact match within one block | Survives line wrapping and `**bold**` without loosening into a similarity judgement that would let a paraphrase pass as grounded | Plan |
| `DiscardReason.user_audit` | Keep the value, build no `DiscardCard` command | An enum value with no caller adds no branch to any path in this slice, unlike the `rejected` status the ADR cut | Plan |
| Note status transitions | Mutating `mark_ready()` / `mark_failed()` on the aggregate | Behavior sits on the aggregate that owns the field, so no caller reaches the status by assignment | Plan |
| Transition guard | Raise `InvalidDistillationTransitionError` outside `generating` | A delivery slipping past the command's idempotency check still cannot rewrite a finished note | Plan |
| Structurally invalid proposal | Command catches `CoreException` per proposal, logs, continues; note still reaches `ready` | One malformed proposal must not cost the user the rest of the run, since zero cards is already a success | Plan |
| Repository verb | One `save` on both ports; `add` removed | S-01's own contract test already pins `add` as an upsert, and `CaptureSessionRepository.save` is the precedent for a mutated aggregate | Plan |
| Deterministic `CardGeneration` | Block-derived proposals plus one deliberately fabricated | Makes the `Discard(ungrounded)` path provable end-to-end by draining the worker, not only in unit tests | Plan |
| `NoteDocumentParser` scope | `resolves` only — no `blocks` | Rendering needs `blocks` and rendering is S-04; S-01 set the precedent of naming only what the slice calls | Plan |
| Acceptance coverage | Gherkin features for US-02 and US-03 | AC-03–AC-06 are the slice's whole acceptance surface and pytest-bdd is already wired with six capture features | Plan |
| `CardProposal` location | Application-layer value object carrying raw strings | Makes the command the layer that builds domain VOs and therefore the layer that catches their construction failures | Plan |

## Scope

**In scope:** `Card` aggregate and its value objects (`CardId`, `CardSide`, `Anchor`, `Discard`, `DiscardReason`, `AnchorResolution`, `CardLengthPolicy`); `CardFactory`; `Note.mark_ready` / `mark_failed`; `CardRepository` and the `add → save` rename on `NoteRepository`; `CardGeneration` and `NoteDocumentParser` ports with in-memory adapters; `GenerateCardsCommand`; `FlashcardGenHandler`; composition, settings, exception mapping; acceptance features for US-02 and US-03.

**Out of scope:** `DiscardCard` command and any caller for `user_audit`; query DTOs, note list and note detail (S-03, S-04); anchor jump (S-05); `NoteDocumentParser.blocks`; a `cards_generated` envelope; regeneration; any timeout or sweeper for a note stranded in `generating`; a surface for reading discarded rows; scheduling state; SQL and LLM adapters.

## Architecture / Approach

The chain is `note_approved → [note-save] → note_saved → [flashcard-gen]`; S-01 built the first handler, this slice builds the second. The grounding invariant splits across two layers as the ADR requires: the application resolves each proposal's quote through the parser port, and the domain judges the verdict. `CardFactory.mint` takes an `AnchorResolution` and always returns a `Card` — live or discarded, never `None`. Evaluation order is fixed: grounding first (outside the configurable policy collection), then `CardLengthPolicy`, first violation wins.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Card VOs & exceptions — stubs | Card vocabulary and five new `CoreException`s | — |
| 2. Card VOs & exceptions — behavior | Construction rules, `CardLengthPolicy.breach` | Exhaustiveness test may force the mapping entries early |
| 3. Card aggregate & factory — stubs | `Card` fields, `CardFactory.mint` signature | — |
| 4. Card aggregate & factory — behavior | Differing-sides invariant, fixed evaluation order | Grounding must be checked before length, not after |
| 5. Note transitions & repo ports — stubs | Transitions, `CardRepository`, `add → save` rename | The rename touches a shipped S-01 symbol |
| 6. Note transitions & repo ports — behavior | Guard, in-memory card repo, two contract suites | — |
| 7. App ports & outbound adapters — stubs | `CardProposal`, both ports, `UoW.cards`, adapter skeletons | — |
| 8. NoteDocumentParser — behavior | The quote-matching rule and its contract suite | Normalization is permanent — a later change breaks old anchors |
| 9. Deterministic CardGeneration — behavior | Block-derived proposals plus one fabricated | Must never emit a structurally invalid proposal |
| 10. Command & handler — stubs | `GenerateCardsCommand`, `FlashcardGenHandler` signatures | — |
| 11. GenerateCardsCommand — behavior | Orchestration, per-proposal catch, status transitions | Idempotency check must precede generation, not follow it |
| 12. FlashcardGenHandler — behavior | Validate, delegate, malformed-envelope path | — |
| 13. Composition | Wiring, settings, exception mapping | Handler order in the worker list is semantic |
| 14. Acceptance scenarios | Features for US-02/US-03, support composition, marker | First BDD coverage the distill pillar has |

**Prerequisites:** S-01 (`distill-flow-note-lands`), archived and done.
**Estimated effort:** 14 phases, seven stubs/behavior pairs plus composition and acceptance; no new external dependencies.

## Open Risks & Assumptions

- The parser's normalization becomes permanent: only the quote is stored, so a later change to how a block's text is produced can retroactively break anchors written months earlier, with no stored fallback.
- The deterministic generator fabricates one proposal on purpose, so the composed system always shows a discard rate above zero — a manual run never sees a clean batch.
- `DiscardReason.user_audit` ships with no caller, which is dead vocabulary until a review surface exists.
- A note can still be stranded in `generating` after `max_attempts` — an ADR-accepted cost this slice does not address.
- Nothing reads discarded rows; the rejection rate is retained (FR-006) and unobserved.

## Success Criteria (Summary)

- Cards exist for a held note with no user action, and every live card's quote resolves within that note (AC-03, AC-05).
- A note producing zero live cards reaches the same `ready` state as one producing many, differing only in card count (AC-04).
- A proposal whose quote is absent from the note is persisted as a discarded card and never appears among live cards (AC-06, FR-006).
