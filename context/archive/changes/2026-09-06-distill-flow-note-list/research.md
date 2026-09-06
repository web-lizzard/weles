---
date: 2026-09-06T00:31:00+02:00
topic: "Functional requirements, domain mapping, and TUI changes for the note list slice"
topic_slug: null
container_id: distill-flow-note-list
tags: [research, distill, note-list, tui, domain]
last_updated: 2026-09-06
---

# Research: Functional requirements, domain mapping, and TUI changes for the note list slice

## Research Question

/research distill-flow-note-list potrzebuje abyś z @context/efforts/distill-flow/prd.md oraz @context/adrs/distill-domain-shape/adr.md wyekstraktował funkcjonalne wymagania, mapowania na domene oraz zmiany wymagane w tui

## Summary

Slice **S-03** (`distill-flow-note-list`) delivers FR-007 through FR-010: a note list showing topic, distillation state, and live card count, ordered by recency, reachable without losing an in-flight capture session. Prerequisites S-01 and S-02 (done) supply the data — notes land automatically (FR-001) and cards generate automatically (FR-002), with zero cards reported as success (FR-005).

The distill domain shape is already settled for listing: the `Note` aggregate carries `topic`, `distillation_status` (`generating | ready | failed`), and timestamps; live card count comes from `Card` rows where `discard is None`. The ADR deliberately left query DTOs and list ordering undecided (`decision.md:116`), so S-03 must add the read path — `ListNotes` query, `GET /notes`, and OpenAPI regen — plus a TUI overlay shell with a `/notes` command that keeps `CaptureScreen` mounted and preserves all capture state in `useChatStore`.

Out of scope for this slice: note detail (S-04 / FR-011–012), card-to-anchor jump (S-05 / FR-013), and the one-time "cards ready" notification (FR-014, deferred in PRD non-goals).

## Findings

### Slice scope and prerequisites

- S-03 outcome matches the change title: users see notes — topic, distillation state, card count — without losing an in-flight capture session (`context/efforts/distill-flow/roadmap.md:13`, `context/changes/distill-flow-note-list/change.md:3`).
- Acceptance criteria AC-07 through AC-10 map to FR-007 through FR-010 (`context/efforts/distill-flow/roadmap.md:49`, `context/efforts/distill-flow/stories.md:45-55`).
- S-01 and S-02 are prerequisites and done (`context/efforts/distill-flow/roadmap.md:22-23`, `:52`). S-04 runs in parallel but is not part of S-03 deliverables (`context/efforts/distill-flow/roadmap.md:53`).

### Functional requirements (from PRD)

#### Primary deliverables (S-03)

| ID | Requirement | Priority | Story |
|----|-------------|----------|-------|
| FR-007 | User can list their notes without leaving or losing an in-flight capture session | must-have | US-04 / AC-07 |
| FR-008 | The note list shows, per note, its topic, its distillation state, and how many cards it has | must-have | US-05 / AC-08 |
| FR-009 | The note list is ordered by the most recent update of a note or of its cards | must-have | US-05 / AC-10 |
| FR-010 | The distillation state distinguishes three cases: generation in progress, completed with zero cards, and generation failed | must-have | US-05 / AC-09 |

Source text: `context/efforts/distill-flow/prd.md:52-55`.

#### Upstream dependencies (data the list displays)

| ID | Requirement | Role |
|----|-------------|------|
| FR-001 | An approved capture note becomes a note held by Weles automatically | Notes must exist before they can be listed |
| FR-002 | Weles generates flashcards from a held note automatically | Card counts and status transitions must be meaningful |
| FR-005 | A note that produces zero cards is reported as a completed distillation, not a failed one | Feeds the "completed with zero cards" case in FR-010 |

Source text: `context/efforts/distill-flow/prd.md:40`, `:44`, `:47`.

#### Guardrail reinforcing FR-007

Browsing notes and cards never interrupts or discards an in-flight capture session (`context/efforts/distill-flow/prd.md:32-33`).

#### Explicitly out of scope for S-03

- **Later slices:** open/read note (FR-011, S-04), see cards on note (FR-012, S-04), jump to anchored fragment (FR-013, S-05) — `context/efforts/distill-flow/roadmap.md:55-70`.
- **FR-014 notification:** nice-to-have in PRD but explicitly a non-goal for this ship; the state badge on the note list carries the fact — `context/efforts/distill-flow/prd.md:59`, `:71`.
- **Whole-effort non-goals** also apply: spaced repetition, manual card removal, regeneration, note editing, external publishing, rejected-proposals surface, semantic search, non-capture note origins — `context/efforts/distill-flow/prd.md:61-70`.

### Domain mapping (from ADR)

The decision body lives in `context/adrs/distill-domain-shape/decision.md`; `adr.md` is frontmatter only.

#### Note aggregate — primary list row source

The `Note` aggregate fields relevant to listing (`backend/src/domain/distill/note.py:16-24`):

| List field | Domain source | ADR |
|------------|---------------|-----|
| Note id | `Note.id` (same as capture note id) | `decision.md:29` |
| Topic | `Note.topic.label` via embedded `TopicSnapshot` | `decision.md:27-30` |
| Distillation state | `Note.distillation_status` | `decision.md:32` |
| Timestamps | `approved_at`, `created_at` | ordering candidates |

New notes mint in `GENERATING` via `mint_note()` (`backend/src/domain/distill/note.py:39-56`, `:53`). Transitions: `mark_ready()` and `mark_failed()` only from `GENERATING` (`backend/src/domain/distill/note.py:26-32`, `:34-36`).

#### DistillationStatus enum

```python
class DistillationStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
```

(`backend/src/domain/distill/value_objects.py:57-60`; ADR: `decision.md:32`)

**FR-010 three-way display mapping** (product cases, not four enum values):

| User-visible case | Condition |
|-------------------|-----------|
| Generation in progress | `distillation_status == GENERATING` |
| Completed with zero cards | `distillation_status == READY` and live card count == 0 |
| Generation failed | `distillation_status == FAILED` |

`READY` with live cards > 0 is normal success, shown via card count (FR-008). Zero cards is success, not failure (`decision.md:32`, FR-005).

A note can remain stranded in `GENERATING` when outbox retries are exhausted — the list must still show "in progress" (`decision.md:134`).

#### Live card count

- `Card.discard: Discard | None` — a card is live only while `discard is None` (`decision.md:46`, `backend/src/domain/distill/card.py:21`).
- `CardRepository.list_by_note()` returns all cards including discarded; the query handler must filter (`decision.md:124`, `backend/src/domain/distill/ports.py:17`).

#### Ordering (FR-009)

The ADR explicitly did not decide query DTOs or list ordering (`decision.md:116`, `:161`). Available timestamps:

- Note: `created_at`, `approved_at` — no `updated_at` on the aggregate.
- Card: `created_at` per live card.

The query must compute recency as the maximum across note timestamps and live card `created_at` values, matching PRD FR-009 and AC-10.

#### ADR constraints on implementation

- No imports from capture into distill — list reads distill store only (`decision.md:107`).
- Topic and tags are embedded snapshots, never resolved from capture repos (`decision.md:27-30`).
- No scheduling state on `Card` — list shows content count only, not review state (`decision.md:42`, `:108`).
- `NoteDocumentParser` is not needed for the list row — parser is for anchoring and detail rendering (`decision.md:98`).

#### Ports gap (to implement in S-03)

| Exists today | Missing for note list |
|--------------|----------------------|
| `NoteRepository.save`, `get` (`backend/src/domain/distill/ports.py:8-11`) | list/scan all notes |
| `CardRepository.list_by_note` (`backend/src/domain/distill/ports.py:14-17`) | OK; filter at query |
| Commands under `application/distill/commands/` | no `queries/`, no `ListNotes` handler |
| HTTP: capture, health, outbox (`backend/src/main.py:35-38`) | no `GET /notes` |

Per CQRS-lite, the query handler reads directly into DTOs without `UnitOfWork.commit()`.

### TUI changes required

#### Current state

- `App` renders only `CaptureScreen` — no router, no overlay (`tui/src/app.tsx:3-5`).
- Sole slash command: `/approve` (`tui/src/screens/CaptureScreen.tsx:13`, `:60-62`).
- API client covers capture only (`tui/src/api/stream.ts:73-100`; OpenAPI paths in `tui/src/api/generated/schema.d.ts:24-68`).
- No note-list tests in `tui/test/`.

#### Required changes by FR

| FR | Backend | TUI |
|----|---------|-----|
| FR-007 | No server change strictly required if session stays client-side | Overlay shell over `CaptureScreen`; `/notes` command; do **not** reset `useChatStore` when opening/closing list (contrast: `approveDraft` clears all state — `tui/src/store/chat.ts:176-188`) |
| FR-008 | `GET /notes` DTO: topic, status, card_count | `NoteListOverlay` rows |
| FR-009 | Query computes `last_updated_at` | Render in that order |
| FR-010 | Expose raw `distillation_status` + `card_count` | Map to three badges: generating / ready+0 / failed |

#### New TUI components

1. **App shell with overlay host** — keep `CaptureScreen` mounted; render command overlay above it (accepted pattern: `context/duck-sessions/distill-pillar/log.md:11-12`, `:96-97`).
2. **Slash-command dispatcher** — route `/notes` separately from prose input and `/approve`.
3. **`NoteListOverlay`** — rows with topic, state badge, card count; keyboard navigation (Enter to drill is S-04).
4. **Notes API client** — typed `GET /notes` via openapi-fetch (`context/adrs/tui-stack/decision.md:18-20`).
5. **Notes store slice** — list data, loading/error, poll loop while overlay is open so `GENERATING` → `READY`/`FAILED` transitions appear (`context/adrs/tui-stack/decision.md:30`).

#### Capture state to preserve (FR-007 / AC-07)

When opening or closing the note list, these `useChatStore` fields must remain intact: `sessionId`, `transcript`, `topic`, `coverageConfidence`, `draft`, `currentReply`, `isStreaming`.

#### Proposed backend read model (S-03 plan territory)

1. `NoteListItemDTO` — `note_id`, `topic_label`, `distillation_status`, `card_count`, `last_updated_at`.
2. `ListNotesQuery` + handler reading straight into DTOs.
3. In-memory query adapter scanning note and card stores.
4. `GET /notes` HTTP route + OpenAPI regen for TUI (`tui/package.json` `generate:api`).

## Code References

- `context/efforts/distill-flow/prd.md:32-33` — guardrail: browsing never interrupts capture
- `context/efforts/distill-flow/prd.md:40` — FR-001 note intake
- `context/efforts/distill-flow/prd.md:44` — FR-002 automatic card generation
- `context/efforts/distill-flow/prd.md:47` — FR-005 zero cards is success
- `context/efforts/distill-flow/prd.md:52-55` — FR-007 through FR-010 note list requirements
- `context/efforts/distill-flow/prd.md:61-71` — non-goals including FR-014 deferral
- `context/efforts/distill-flow/prd.md:77-78` — open questions Q3 (stuck generating) and Q4 (gesture to list)
- `context/efforts/distill-flow/roadmap.md:13` — S-03 outcome
- `context/efforts/distill-flow/roadmap.md:22-23` — S-01/S-02 prerequisites for S-03
- `context/efforts/distill-flow/roadmap.md:46-53` — S-03 acceptance criteria and parallel-with-S-04
- `context/efforts/distill-flow/stories.md:39-55` — US-04/US-05 and AC-07 through AC-10
- `context/changes/distill-flow-note-list/change.md:3` — change title mirrors S-03 outcome
- `context/adrs/distill-domain-shape/decision.md:27-32` — Note aggregate fields and distillation_status semantics
- `context/adrs/distill-domain-shape/decision.md:42` — no scheduling state on Card
- `context/adrs/distill-domain-shape/decision.md:46` — live card = no discard
- `context/adrs/distill-domain-shape/decision.md:96-99` — repository and parser ports
- `context/adrs/distill-domain-shape/decision.md:107-108` — no capture imports; no scheduling on Card
- `context/adrs/distill-domain-shape/decision.md:116` — query DTOs and ordering deliberately not decided
- `context/adrs/distill-domain-shape/decision.md:124` — every card read must exclude discarded
- `context/adrs/distill-domain-shape/decision.md:134` — note can be stranded in generating
- `context/adrs/distill-domain-shape/decision.md:161` — query DTOs rejected as ADR scope
- `context/adrs/tui-stack/decision.md:17-20` — Zustand for cross-screen state; openapi-fetch for REST
- `context/adrs/tui-stack/decision.md:30` — background polling for distillation completion
- `context/duck-sessions/distill-pillar/log.md:11-12` — overlay preserves capture session
- `context/duck-sessions/distill-pillar/log.md:96-97` — overlay never unmounts CaptureScreen
- `backend/src/domain/distill/note.py:16-24` — Note aggregate fields
- `backend/src/domain/distill/note.py:26-32` — mark_ready / mark_failed transitions
- `backend/src/domain/distill/note.py:53` — mint_note sets GENERATING
- `backend/src/domain/distill/value_objects.py:28-30` — TopicSnapshot with label
- `backend/src/domain/distill/value_objects.py:57-60` — DistillationStatus enum
- `backend/src/domain/distill/card.py:21-22` — discard field and created_at
- `backend/src/domain/distill/ports.py:8-17` — NoteRepository and CardRepository ports
- `backend/src/main.py:35-38` — HTTP routers mounted (no distill notes route yet)
- `backend/src/application/distill/commands/generate_cards.py:44-47` — mark_failed on generation error
- `backend/src/application/distill/commands/generate_cards.py:71-72` — mark_ready after generation
- `backend/tests/unit/distill/test_generate_cards_command.py:75-76` — live vs discarded card filter pattern
- `tui/src/app.tsx:3-5` — single-screen capture-only App
- `tui/src/screens/CaptureScreen.tsx:13` — /approve command constant
- `tui/src/screens/CaptureScreen.tsx:60-62` — slash command dispatch
- `tui/src/store/chat.ts:176-188` — approveDraft clears session (anti-pattern for note list)
- `tui/src/api/stream.ts:73-100` — capture-only API functions

## Open Questions

1. **Gesture to reach the note list (PRD Q4):** "By what gesture does the user reach the note list — the command set for the shell is not settled." Owner: implementation, resolved at `/plan`. Directional consensus from duck session: `/notes` slash command (`context/efforts/distill-flow/prd.md:78`, `context/duck-sessions/distill-pillar/log.md:12`).

2. **Stuck in generating (PRD Q3):** A note can sit in "generation in progress" forever — no timeout or sweeper. Does the user need retry, or is a visible failed state enough? The list must show generating even when stuck (`context/efforts/distill-flow/prd.md:77`, `decision.md:134`).

3. **`last_updated_at` computation:** Exact formula for FR-009 ordering is not decided in ADR; plan must define whether status transitions (mark_ready/mark_failed) contribute a timestamp beyond note and card `created_at`/`approved_at`.
