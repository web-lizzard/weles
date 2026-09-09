---
date: 2026-09-08T15:30:00+02:00
topic: "What distill-flow-card-anchor-jump must deliver given requirements, backend domain, and current TUI state"
topic_slug: null
container_id: distill-flow-card-anchor-jump
tags: [research, distill-flow, tui, backend, anchor-jump]
last_updated: 2026-09-08
---

# Research: Card-to-anchor jump scope

## Research Question

/research destylacja requirments, obecny stan tui oraz domeny backendu. Co trzeba zrobić distill-flow-card-anchor-jump

## Summary

Slice S-05 (`distill-flow-card-anchor-jump`) realizes AC-13 and FR-013: from a card the user reaches its note with the source fragment distinguished from the rest of the content. Prerequisites S-04 (note detail, AC-11) and S-06 (cards tab, AC-12) are done. The change container exists but has no plan yet.

The backend already stores a verbatim `anchor.quote` on every card and exposes it as `anchor_quote` on `GET /notes/{note_id}/cards`, alongside full note `content` on `GET /notes/{note_id}`. Grounding at generation time uses block-normalized substring matching via `NoteDocumentParser`. There are no offsets, block indices, or highlight metadata on the wire.

The TUI delivers the full note/cards browsing stack from S-04 and S-06 — tab strip, card list, card detail, and `anchorQuote` display — but has no jump gesture, no anchor state in the store, and renders note content as a single undifferentiated text block. AC-13 work is therefore greenfield in the TUI, with an open `/plan` decision on whether anchor resolution stays client-side (reusing the parser's normalization rules) or moves to a backend read-model extension.

## Findings

### Requirements (AC-13 / FR-013)

US-07 realizes FR-013. AC-13 states: from a card the user reaches its note with the source fragment distinguished from the rest of the content. FR-013 adds that the fragment must be marked in the note view. Both are must-have.

Upstream requirements already satisfied by prior slices supply the data AC-13 needs: FR-003 (every card cites a verbatim fragment → `anchor.quote`), FR-004 (ungrounded cards never reach the user), FR-011 (open and read full note content → S-04), FR-012 (see cards from an open note → S-06).

The ADR rejected stored character offsets and block indices in favor of quote-at-read-time resolution (`decision.md:154-155`). Block position for a jump gesture is derived at read time, not persisted. The matching rule — normalize rendered block text, collapse whitespace, strip inline emphasis, require single-block resolution — lives in the adapter parser, not the domain aggregate.

No BDD feature file covers US-07 or AC-13. Existing distill-flow BDD covers grounding (AC-05/06) and the note list (AC-08–10) only.

### Backend domain and API

`Anchor` is a quote-only value object: stripped, non-empty, max 4000 characters. `Card.anchor` is mandatory on every card; live cards have `discard is None`. `Note` carries full `content` with no anchor fields.

At generation, `GenerateCards` calls `NoteDocumentParser.resolves(note.content, proposal.quote)`. Unresolved anchors mint a `Discard(ungrounded)` card that is filtered from all user-facing reads. The in-memory parser splits content on blank lines into blocks, normalizes each block (strip leading markdown markers, remove inline emphasis chars, collapse whitespace), and checks whether the normalized quote is a substring of any normalized block.

API surface today:
- `GET /notes/{note_id}` → `NoteDetailDTO` with plain `content` string, no anchor metadata.
- `GET /notes/{note_id}/cards` → `CardListItemDTO` list with `anchor_quote` from `card.anchor.quote`, live cards only, sorted by `created_at` ascending.

Prior slices explicitly deferred anchor jump and fragment highlighting to S-05. The backend supplies the minimum data for client-side quote matching but implements no AC-13-specific endpoint or structured jump metadata.

### TUI current state

Navigation shell: `/notes` opens the overlay; Enter on a ready note opens detail; `Note` / `Cards` tab strip; `→` switches to cards when `cardCount > 0`; card list shows front, back preview, and `anchorQuote`; Enter opens card detail; `←` returns; ESC unwinds to capture.

`Card` type and API map `anchor_quote` → `anchorQuote`. `NoteDetail` type has plain `content` only. `useAppStore` tracks `activeNoteTab` and `selectedCardId` but has no `highlightedAnchorQuote` or equivalent jump-target state. `NoteDetailScreen` renders `note.content` as one `<Text wrap="wrap">` with no fragment distinction.

`CardDetailScreen` handles only `leftArrow` (close card). No key binding jumps to the note tab with anchor context. Tests cover tab navigation and `anchorQuote` display; zero tests cover anchor jump or highlight.

### What S-05 must deliver

Core AC-13 work (TUI, regardless of backend choice):

1. **Jump gesture** from card detail (and possibly card list) to the note tab with anchor context preserved in store.
2. **Store extension** — e.g. `highlightedAnchorQuote` set on jump, cleared on tab/note close.
3. **Fragment distinction** in `NoteDetailScreen` — match `anchorQuote` against `note.content` and render the passage visually distinct from surrounding text.
4. **Tests** for jump navigation and highlight rendering.

Open `/plan` decisions:

| Decision | Options |
|----------|---------|
| Where to resolve anchor | TUI-only (replicate `NoteDocumentParser` normalization) vs backend extension (`blocks()` or resolved position on `NoteDetailDTO`) |
| Jump gesture | e.g. `→` from `CardDetailScreen`, Enter on card list row — not yet specified |
| Long-note scroll | S-04 deferred scrolling; without it a highlighted fragment below the viewport may be invisible |
| Quote-not-found fallback | Show note without highlight vs error state |

Backend work is optional if the plan chooses client-side resolution. If server-side, add parser exposure or DTO extension plus optional BDD for US-07. If TUI-only, existing `anchor_quote` + `content` suffice.

Explicitly out of scope (effort non-goals, unchanged by S-05): spaced repetition, manual card removal, regeneration, note editing, rejected-proposal inspection, semantic search, FR-014 one-time notification.

## Code References

- `context/efforts/distill-flow/stories.md:66-72` — US-07 and AC-13 definition
- `context/efforts/distill-flow/prd.md:58` — FR-013 must-have requirement
- `context/efforts/distill-flow/roadmap.md:67-73` — S-05 slice, prerequisites S-04 + S-06
- `context/changes/distill-flow-card-anchor-jump/change.md:15` — no plan yet; next step is `/plan`
- `context/adrs/distill-domain-shape/decision.md:154-155` — quote-at-read-time, no stored offsets or block index
- `backend/src/domain/distill/card.py:15-22` — `Card` with mandatory `anchor: Anchor`
- `backend/src/domain/distill/value_objects.py:86-102` — `Anchor.quote` value object
- `backend/src/adapters/out/in_memory/distill/note_document_parser.py:11-29` — block split, normalization, substring resolution
- `backend/src/application/distill/queries/list_cards_for_note.py:10-15` — `CardListItemDTO` with `anchor_quote`
- `backend/src/application/distill/queries/get_note.py:20-28` — `NoteDetailDTO` with plain `content`
- `backend/src/adapters/http/notes.py:32-45` — `GET /notes/{note_id}` and `GET /notes/{note_id}/cards`
- `backend/tests/features/distill-flow/US-03-grounded-cards.feature:4-22` — grounding BDD only; no jump coverage
- `tui/src/app.tsx:53-60` — screen dispatch: note detail / card list / card detail
- `tui/src/store/index.ts:10-11,58-60` — `activeNoteTab`, `selectedCardId`; no anchor state
- `tui/src/screens/NoteDetailScreen.tsx:47` — plain `note.content` render, no highlight
- `tui/src/screens/CardDetailScreen.tsx:19-22,30-32` — only `leftArrow`; displays `anchorQuote` without jump
- `tui/src/screens/CardListScreen.tsx:94-96` — `anchorQuote` on list rows
- `tui/src/api/cards.ts:3-8,23` — `Card.anchorQuote` mapped from `anchor_quote`
- `tui/src/api/notes.ts:13-22` — `NoteDetail.content` plain string
- `context/archive/changes/2026-09-06-distill-flow-note-cards/plan.md:36` — anchor jump explicitly deferred to S-05
- `context/archive/changes/2026-09-06-distill-flow-note-detail/research.md:111-113` — anchor resolution deferred; quote display only in S-06

## Open Questions

1. **TUI-only vs backend resolution** — ADR favors quote-at-read-time; parser exists server-side. Does S-05 port normalization to TypeScript or expose resolved block position from a query handler?
2. **Jump gesture** — which key from `CardDetailScreen` (and/or `CardListScreen`) triggers the jump?
3. **Scroll to fragment** — is highlighting within the first viewport enough, or does S-05 need Ink scroll support deferred from S-04?
4. **US-07 BDD** — should S-05 add a `backend/tests/features/distill-flow/US-07-*.feature` for AC-13, or is TUI test coverage sufficient?
5. **Quote-not-found UX** — if client-side matching fails (formatting drift, empty quote edge case), what does the user see?
