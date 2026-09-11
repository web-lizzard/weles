---
date: 2026-09-11T16:00:00+02:00
topic: "Implementation state of note anchors — public API, construction, verbatim vs paraphrase"
topic_slug: null
container_id: remember-flow-source-jump
tags: [research, distill, remember, anchors, notes, tui]
last_updated: 2026-09-11
---

# Research: Implementation state of note anchors — public API, construction, verbatim vs paraphrase

## Research Question

/research remember-flow-source-jump

stan implementacji anchore w notes - jakie publiczne api wystawiane - jak są budowane - czy brane są dosłowne cytaty z notatki, czy mogą być to parafraowane wartości

## Summary

Anchors in notes are implemented end-to-end in **distill** (stored `Anchor.quote` on each `Card`, read-time `anchor_location`, HTTP on note/card list routes, TUI browse jump/highlight). The **remember-flow-source-jump** change (slice S-05) is still a stub: review sittings expose no anchor fields and source jump during review is not built yet; it should reuse distill’s quote + `NoteDocument.locate` semantics without redefining them.

Public API today: `GET /notes/{note_id}` returns note `blocks`; `GET /notes/{note_id}/cards` returns `anchor_quote` and nullable `anchor_location` (`block_index`, `start`, `end`, `precision`). Anchors are built at card generation from `CardProposal.quote`, grounded via normalized substring search in a single block; ungrounded proposals are discarded but keep the quote. Product and ADR require **verbatim excerpts** from the note’s wording—paraphrases do not resolve and fail grounding; normalization tolerates markdown formatting differences, not rewording.

## Findings

### Container and effort context

- `remember-flow-source-jump` is materialized with status `new` and no `plan.md` or `frame.md` yet (`context/changes/remember-flow-source-jump/change.md:2-15`).
- Parent effort slice S-05 targets AC-18–20: jump to source fragment under review; card stays reviewable when fragment is missing (`context/efforts/remember-flow/stories.md:97-112`).
- Shipped distill anchor-jump (browse path) lives in archived change `2026-09-08-distill-flow-card-anchor-jump`; remember review jump is the remaining gap.

### Domain model (distill)

- `Anchor` is a frozen value object with a single field `quote: str` (strip, non-empty, max length) (`backend/src/domain/distill/value_objects.py:86-102`).
- ADR: anchor holds a **verbatim quote**; how matching works is not decided on the aggregate (`context/adrs/distill-domain-shape/decision.md:40-46`).
- Every `Card` carries `anchor: Anchor`; live vs discarded is separate from anchor shape (`backend/src/domain/distill/card.py:15-22`).
- Grounding at mint: `GenerateCardsCommand` builds `Anchor(quote=proposal.quote)`, runs `NoteDocument.of(content).locate(anchor)`, passes `AnchorResolution` to `CardFactory.mint`; `UNRESOLVED` → `DiscardReason.UNGROUNDED` while quote remains on the card (`backend/src/application/distill/commands/generate_cards.py:49-62`, `backend/src/domain/distill/card_factory.py:47-51`).

### Location resolution (read-time, not persisted)

- `NoteDocument.locate` normalizes the quote, searches each block with `normalized.value.find(quote.value)`, maps back to raw indices via `MarkdownNoteFormat` offset map (`backend/src/domain/distill/note_document.py:46-85`, `backend/src/domain/distill/note_format.py:19-57`).
- `AnchorPrecision.EXACT` vs `BLOCK` affects highlight/jump granularity only, not what text may be stored in `quote` (`backend/src/domain/distill/note_document.py:11-14`, `71-95`).
- `anchor_location` on list-cards is always recomputed from current note content + stored quote (`backend/src/adapters/out/in_memory/distill/list_cards_for_note_query.py:28-35`).

### Public HTTP API

- Routes on notes router: `GET /notes/{note_id}` → `NoteDetailDTO` with `blocks: list[NoteBlockDTO]`; `GET /notes/{note_id}/cards` → `list[CardListItemDTO]` with `anchor_quote` and `anchor_location` (`backend/src/adapters/http/notes.py:32-45`, `backend/src/application/distill/queries/get_note.py:20-29`, `backend/src/application/distill/queries/list_cards_for_note.py:10-22`).
- No GraphQL. Remember HTTP has no anchor/quote fields; `ReviewableCard` is id + front + back only (`backend/src/domain/remember/ports.py:14-17`, `backend/src/adapters/out/in_memory/remember/review_catalog.py:42-47`).
- Empty anchor at validation maps to `empty_anchor` → 422 (`backend/src/adapters/http/errors.py:38`).

### Generation pipeline today

- Only in-memory `DeterministicCardGenerationAdapter` is wired; no LLM adapter under `backend/src` (`backend/src/adapters/compose.py:123`, `backend/src/adapters/out/in_memory/distill/card_generation.py:38-45`).
- Block-derived proposals set `quote` to the **full raw block text** (verbatim paragraph), not a model paraphrase (`card_generation.py:38-45`).
- Contract tests require every block proposal’s quote to `locate` except one fabricated unresolvable sentinel (`backend/tests/unit/distill/contracts/test_card_generation_contract.py:29-57`).

### Verbatim vs paraphrase

- Grounding is exact normalized substring in one block; archived grounded-generation plan states no similarity judgement—paraphrase must not pass (`context/archive/changes/2026-09-04-distill-flow-grounded-generation/plan.md:422-424`).
- Tests: quote without markup resolves against note with emphasis; absent text → `None` (`backend/tests/unit/distill/test_note_document.py:14-38`, `82-83`); HTTP asserts `exact_block[start:end] == exact_quote` for exact precision (`backend/tests/integration/test_notes_http.py:248-265`).
- ADR consequence: paraphrase → lost (ungrounded) cards (`context/adrs/distill-domain-shape/decision.md:135`).
- Product distill FR-003 / AC-05: fragment quoted as in the note (`context/efforts/distill-flow/prd.md:45`, `context/efforts/distill-flow/stories.md:36`).

### TUI (distill browse only)

- Client types and mapping: `anchorQuote`, `anchorLocation` (`tui/src/api/cards.ts:3-53`).
- `CardDetailScreen` calls `jumpToAnchor`; `NoteDetailScreen` highlights `block.text[start:end]` (`tui/src/screens/CardDetailScreen.tsx:32`, `tui/src/screens/NoteDetailScreen.tsx:23-40`).
- Review overlay has no source-jump wiring yet (aligns with S-05 scope).

## Code References

- `backend/src/domain/distill/value_objects.py:86-113` — `Anchor`, `AnchorResolution`, validation
- `backend/src/domain/distill/note_document.py:11-95` — `AnchorLocation`, `AnchorPrecision`, `locate`
- `backend/src/domain/distill/note_format.py:19-57` — blocks, normalization, offsets
- `backend/src/domain/distill/card.py:15-22` — `Card.anchor`
- `backend/src/domain/distill/card_factory.py:47-51` — ungrounded discard keeps quote
- `backend/src/application/distill/commands/generate_cards.py:49-62` — anchor build + resolution at generation
- `backend/src/application/distill/queries/list_cards_for_note.py:10-22` — wire DTOs for anchors
- `backend/src/application/distill/queries/get_note.py:20-29` — `NoteBlockDTO` / blocks on note detail
- `backend/src/adapters/http/notes.py:32-45` — public GET routes
- `backend/src/adapters/out/in_memory/distill/list_cards_for_note_query.py:28-52` — `anchor_quote` + derived `anchor_location`
- `backend/src/adapters/out/in_memory/remember/review_catalog.py:42-47` — anchors stripped at remember boundary
- `backend/src/adapters/out/in_memory/distill/card_generation.py:38-45` — deterministic `quote` = block text
- `tui/src/api/cards.ts:3-53` — client anchor mapping
- `tui/src/screens/NoteDetailScreen.tsx:23-40` — highlight slice
- `context/adrs/distill-domain-shape/decision.md:40-46` — verbatim quote ADR
- `context/changes/remember-flow-source-jump/change.md:2-15` — change stub, no plan yet
- `context/efforts/remember-flow/stories.md:97-112` — US-10/11 acceptance criteria for review jump

## Open Questions

- Exact remember-layer HTTP/TUI contract for S-05: which fields on sitting DTOs vs reusing distill `GET` routes with `note_id` from catalog.
- Future LLM `CardGeneration` adapter: prompts must emit locatable quotes; paraphrase behavior is already defined by grounding, not by a separate review rule.
