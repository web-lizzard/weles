---
date: 2026-09-06T21:47:00+02:00
topic: "Distill domain mapping, TUI requirements for note detail, and list keyboard navigation"
topic_slug: null
container_id: distill-flow-note-detail
tags: [research, distill, note-detail, tui, domain, keyboard-navigation]
last_updated: 2026-09-06
---

# Research: Distill domain mapping, TUI requirements for note detail, and list keyboard navigation

## Research Question

/research wydestyluj domene oraz wymagania co do tui - dodatkowo zalezy mi na tym aby w tui w liscie strzałkami dało się przechodzić pomiędzy elementami listy - kolor aktywnego itemu - niebieski

## Summary

Slice **S-04** (`distill-flow-note-detail`) delivers FR-011 and FR-012: the user opens a note from the list, reads its full content, and sees the live cards it produced. Prerequisites S-01 through S-03 (done) supply the data — notes land automatically, cards generate automatically, and the note list overlay (`/notes`) already shows topic, distillation state, and card count without disturbing an in-flight capture session.

The distill domain already holds everything a detail view needs on the `Note` and `Card` aggregates, but the read path stops at `ListNotesQueryPort` / `GET /notes`. S-04 must add a `GetNote` query (or equivalent), a `GET /notes/{note_id}` route, OpenAPI regen, and TUI screens for note detail. List-to-detail navigation is **selection-addressed** per the duck session (`/notes` → list → Enter → note); the user additionally requires **arrow-key row navigation** with the active row highlighted in **blue** — not spelled out in the PRD but compatible with the selection-addressed flow.

Out of scope for S-04: card-to-anchor jump (S-05 / FR-013) and the one-time "cards ready" notification (FR-014, deferred in PRD non-goals).

## Findings

### Slice scope and prerequisites

- S-04 outcome: users can open a note and read what it produced (`context/efforts/distill-flow/roadmap.md:14`, `context/changes/distill-flow-note-detail/change.md:3`).
- Acceptance criteria AC-11 and AC-12 map to FR-011 and FR-012 (`context/efforts/distill-flow/roadmap.md:58`, `context/efforts/distill-flow/stories.md:63-64`).
- S-01, S-02, and S-03 are prerequisites and done (`context/efforts/distill-flow/roadmap.md:22-24`, `:74-76`). S-05 (card anchor jump) is a later slice (`context/efforts/distill-flow/roadmap.md:15`, `:68-70`).

### Functional requirements (from PRD)

#### Primary deliverables (S-04)

| ID | Requirement | Priority | Story |
|----|-------------|----------|-------|
| FR-011 | User can open a note and read its full content inside Weles | must-have | US-06 / AC-11 |
| FR-012 | User can see the cards generated from an open note | must-have | US-06 / AC-12 |

Source text: `context/efforts/distill-flow/prd.md:56-57`.

#### Upstream dependencies (already shipped)

| ID | Requirement | Role |
|----|-------------|------|
| FR-007 | User can list notes without losing an in-flight capture session | List overlay is the entry point to detail |
| FR-008 | Note list shows topic, distillation state, card count | Row content already rendered in `NoteListOverlay` |
| FR-009 | List ordered by most recent update of note or cards | Backend `last_updated_at` ordering via `ListNotesQueryPort` |
| FR-010 | Three-way distillation state display | Badge mapping already implemented in S-03 |

Source text: `context/efforts/distill-flow/prd.md:52-55`.

#### Guardrail reinforcing FR-007

Browsing notes and cards never interrupts or discards an in-flight capture session (`context/efforts/distill-flow/prd.md:32-33`). The overlay pattern in `tui/src/app.tsx:24-38` keeps `CaptureScreen` mounted; `useChatStore` fields are unchanged across overlay open/close (verified in `tui/test/app.test.tsx:121-154`).

#### Explicitly out of scope for S-04

- **S-05:** jump from a card to its anchored fragment in the note view (FR-013 / AC-13) — `context/efforts/distill-flow/roadmap.md:15`, `:68-70`.
- **FR-014:** one-time "cards ready" notification — nice-to-have in PRD, deferred as a non-goal (`context/efforts/distill-flow/prd.md:59`, `:71`).
- **Whole-effort non-goals** also apply: spaced repetition, manual card removal, regeneration, note editing, external publishing, rejected-proposals surface, semantic search, non-capture note origins — `context/efforts/distill-flow/prd.md:61-70`.

### Domain mapping

The decision body lives in `context/adrs/distill-domain-shape/decision.md`.

#### Note aggregate — detail view source

`Note` fields (`backend/src/domain/distill/note.py:16-25`):

| Detail field | Domain source | ADR |
|--------------|---------------|-----|
| Note id | `Note.id` (same as capture note id) | `decision.md:29` |
| Topic | `Note.topic` (`TopicSnapshot`: `id`, `label`) | `decision.md:27-30` |
| Full content | `Note.content.value` (`NoteContent`, max 20 000 chars) | `decision.md:27-30` |
| Tags | `Note.tags` (`list[TagSnapshot]`) | `decision.md:27-30` |
| Distillation state | `Note.distillation_status` | `decision.md:32` |
| Timestamps | `approved_at`, `created_at`, `updated_at` | ordering / context |

New notes mint in `GENERATING` via `mint_note()` (`backend/src/domain/distill/note.py:45-64`). Transitions: `mark_ready()` and `mark_failed()` only from `GENERATING` (`backend/src/domain/distill/note.py:27-35`); repeat calls raise `InvalidDistillationTransitionError` (`backend/src/domain/distill/exceptions.py:28-29`).

#### DistillationStatus enum

```python
class DistillationStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
```

(`backend/src/domain/distill/value_objects.py:57-60`; ADR: `decision.md:32`)

`READY` with zero live cards is success, not failure (FR-005, `decision.md:32`). A note can remain stranded in `GENERATING` when outbox retries are exhausted — the detail view must still render it (`decision.md:134`).

#### Card aggregate — cards panel source

`Card` fields (`backend/src/domain/distill/card.py:15-22`):

| Detail field | Domain source | ADR |
|--------------|---------------|-----|
| Card id | `Card.id` | `decision.md:35` |
| Front / back | `Card.front.value`, `Card.back.value` | `decision.md:35` |
| Source fragment | `Card.anchor.quote` | `decision.md:40-41` |
| Live vs discarded | `Card.discard is None` | `decision.md:41`, `decision.md:124` |

`CardRepository.list_by_note()` returns all cards including discarded; the detail query must filter to live cards only (`decision.md:124`, `backend/src/domain/distill/ports.py:17-18`, `backend/src/adapters/out/in_memory/distill/list_notes_query.py:15-19`).

Discard reasons exist (`UNGROUNDED`, `OVERSIZED`, `USER_AUDIT` at `value_objects.py:105-108`) but discarded cards must not surface in user-facing reads (`decision.md:124`).

#### Anchor resolution (S-05 prep, not S-04 deliverable)

Anchor matching is an adapter concern, not domain (`decision.md:40-41`). The stored quote is the only persisted anchor; block position is derived at read time (`decision.md:155`). The in-memory parser splits markdown into blocks and normalizes for substring match (`backend/src/adapters/out/in_memory/distill/note_document_parser.py:11-29`). S-05 will need equivalent resolution for the jump gesture; S-04 only displays `anchor.quote` on each card row.

#### Existing read path vs gap

| Capability | Status | Location |
|------------|--------|----------|
| `ListNotesQueryPort` + `NoteListItemDTO` | Implemented | `backend/src/application/distill/queries/list_notes.py:8-17` |
| `GET /notes` | Implemented | `backend/src/adapters/http/notes.py:14-18` |
| `NoteRepository.get` + `CardRepository.list_by_note` | Implemented (domain ports) | `backend/src/domain/distill/ports.py:8-18` |
| `GetNote` query port + detail DTO | **Missing** | — |
| `GET /notes/{note_id}` | **Missing** | OpenAPI: `tui/src/api/generated/schema.d.ts:75-91` |

#### Proposed detail DTO shape (derived, not yet implemented)

**Note section:** `note_id`, `topic` (`{id, label}`), `content`, `tags` (`[{id, label}]`), `distillation_status`, `approved_at`, `created_at`, `updated_at`.

**Cards section (live only):** `[{ card_id, front, back, anchor_quote, created_at }]`.

This mirrors the list DTO naming convention (`note_id`, snake_case on the wire, camelCase in the TUI client per `tui/src/api/notes.ts:11-23`).

### TUI requirements

#### Navigation model

The duck session settled selection-addressed navigation (`context/duck-sessions/distill-pillar/log.md:12`):

> `/notes` → list → Enter → note → a shortcut/command into its cards.

S-03 deliberately deferred Enter-to-drill (`context/archive/changes/2026-09-06-distill-flow-note-list/research.md:159`). S-04 owns that gesture.

The user additionally requires **arrow-key list navigation** with the **active row in blue**. This is not in the PRD but is the natural way to choose a row before pressing Enter in a terminal UI.

#### Implemented (S-03)

| Capability | Evidence |
|------------|----------|
| `/notes` opens overlay over mounted `CaptureScreen` | `tui/src/screens/CaptureScreen.tsx:63-65`, `tui/src/app.tsx:24-38` |
| Rows: topic, status badge, card count | `tui/src/screens/NoteListOverlay.tsx:44-49` |
| Three-way status (generating / failed / ready+zero via `0 cards`) | `tui/src/screens/NoteListOverlay.tsx:56-71` |
| Poll while overlay open | `tui/src/hooks/useNotesPolling.ts:4-8` |
| ESC closes overlay | `tui/src/app.tsx:17-20` |
| Capture input unfocused while overlay open | `tui/src/screens/CaptureScreen.tsx:103` |

#### Missing (S-04)

| Capability | Requirement |
|------------|-------------|
| `selectedIndex` state on the note list | User request + selection-addressed flow |
| Arrow up/down moves selection | User request |
| Active row highlighted in blue | User request |
| Enter opens selected note | AC-11 / FR-011 |
| Note detail screen (content + cards) | AC-11, AC-12 / FR-011, FR-012 |
| `GET /notes/{id}` client + store | Backend detail endpoint |
| ESC from detail returns to list (not capture) | Implied by overlay drill-in |

No note detail screen file exists under `tui/src/screens/` — only `CaptureScreen.tsx` and `NoteListOverlay.tsx`.

#### Keyboard implementation guidance (Ink 7.x)

Project uses `ink@^7.0.0` (resolved `7.1.1` in `tui/pnpm-lock.yaml`). Arrow keys are **`key.upArrow`** and **`key.downArrow`** — not `key.up` / `key.down` ([Ink `useInput` docs](https://github.com/vadimdemedes/ink#useinputinputhandler-options)).

Recommended pattern for the rich multi-line rows in `NoteListOverlay`:

1. Hold `selectedIndex` in component state (or `useNotesStore`).
2. Register `useInput` with `{ isActive: isNotesOverlayOpen && !isDetailOpen }` so it does not compete with capture input or the detail view.
3. On `key.upArrow` / `key.downArrow`, clamp index to `[0, items.length - 1]`.
4. On `key.return`, navigate to detail for `items[selectedIndex]`.
5. Render active row with `<Text color="blue">` — the same convention `ink-select-input` uses in its default `Item` component ([source](https://github.com/vadimdemedes/ink-select-input/blob/master/src/Item.tsx)).

`ink-select-input` is **not** installed (`tui/package.json:22-28`); given multi-line rows (topic + badge + card count), a custom `selectedIndex` approach fits better than adopting `SelectInput` wholesale. Optional `j`/`k` vim bindings are a nice-to-have, not required.

`app.tsx` already owns a top-level `useInput` for ESC (`tui/src/app.tsx:17-20`). Arrow and Enter handling can live in `NoteListOverlay` (with `isActive`) or move to `app.tsx` alongside ESC — either works as long as only one hook is active at a time.

#### Overlay shell constraints (from S-03 plan)

Ink has no z-index — "overlay" means conditionally rendering alongside `CaptureScreen` in the same tree (`context/archive/changes/2026-09-06-distill-flow-note-list/plan.md:33`). Detail view can replace list content inside the same absolute-positioned `Box` (`tui/src/app.tsx:27-38`) or nest as a second conditional render; `CaptureScreen` must stay mounted throughout.

## Code References

- `backend/src/domain/distill/note.py:16-25` — `Note` aggregate fields
- `backend/src/domain/distill/note.py:27-35` — `mark_ready()` / `mark_failed()` transitions
- `backend/src/domain/distill/card.py:15-22` — `Card` aggregate fields
- `backend/src/domain/distill/value_objects.py:57-60` — `DistillationStatus` enum
- `backend/src/domain/distill/ports.py:8-18` — `NoteRepository` and `CardRepository` read ports
- `backend/src/application/distill/queries/list_notes.py:8-17` — existing `NoteListItemDTO` and `ListNotesQueryPort`
- `backend/src/adapters/http/notes.py:14-18` — `GET /notes` (only notes route today)
- `backend/src/adapters/out/in_memory/distill/list_notes_query.py:14-34` — live-card filter and recency ordering
- `backend/src/adapters/out/in_memory/distill/note_document_parser.py:11-29` — anchor block resolution (S-05)
- `context/adrs/distill-domain-shape/decision.md:27-41` — Note/Card shape
- `context/adrs/distill-domain-shape/decision.md:124` — live-card-only reads
- `context/adrs/distill-domain-shape/decision.md:155` — quote-only anchor, position derived at read time
- `context/efforts/distill-flow/prd.md:52-57` — FR-007 through FR-012
- `context/efforts/distill-flow/stories.md:57-64` — US-06 acceptance criteria
- `context/duck-sessions/distill-pillar/log.md:12` — selection-addressed navigation intent
- `context/archive/changes/2026-09-06-distill-flow-note-list/research.md:159` — Enter-to-drill deferred to S-04
- `tui/src/app.tsx:17-38` — ESC handler and overlay shell
- `tui/src/screens/NoteListOverlay.tsx:24-71` — list rendering (no selection yet)
- `tui/src/screens/CaptureScreen.tsx:63-65` — `/notes` dispatch
- `tui/src/api/notes.ts:11-23` — `listNotes()` client (no detail function)
- `tui/package.json:22-28` — Ink 7.x, no `ink-select-input`

## External References

- <https://github.com/vadimdemedes/ink#useinputinputhandler-options> — "`If an arrow key was pressed, the corresponding property will be true`" (`key.upArrow`, `key.downArrow`)
- <https://github.com/vadimdemedes/ink/blob/master/examples/use-input/use-input.tsx> — official arrow-key navigation example
- <https://github.com/vadimdemedes/ink#color> — "`Change text color.` Ink uses chalk under the hood"
- <https://github.com/vadimdemedes/ink-select-input/blob/master/src/Item.tsx> — default selected-item styling: `<Text color={isSelected ? 'blue' : undefined}>`

## Open Questions

1. **Detail layout** — single scrollable view (content above cards) vs split pane? Not decided in PRD; `/plan` should settle.
2. **Empty note list** — arrow navigation with zero items: no-op; confirm in plan.
3. **Detail while `generating`** — show partial content with status badge, or block open until `ready`/`failed`? PRD does not forbid opening a generating note; plan should decide.
4. **Backend detail route shape** — flat DTO vs nested `{ note, cards }`? Follow existing CQRS-lite query package conventions (`application/capture/queries/transcript.py`).
