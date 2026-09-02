---
date: 2026-09-02T22:27:00+02:00
topic: "Preliminary distill domain shape extracted from the distill-pillar duck session"
topic_slug: null
container_id: distill-domain-shape
tags: [research, distill, domain-model, aggregates, outbox, duck-session]
last_updated: 2026-09-02
---

# Research: Preliminary distill domain shape extracted from the distill-pillar duck session

## Research Question

/research distil-domain-shape wyekstraktuj mi z sesji duck załączonej do kontenera wstepny kształ domeny

## Summary

Distill is the middle pillar (`capture → distill → remember`). Its domain begins where capture ends: an approved note and a `note_approved` outbox envelope written inside the same `UnitOfWork` by `ApproveNote`. Distill never reads capture repositories — it works from the denormalized snapshot in the envelope.

The duck session `distill-pillar` (container `origin`) settled three aggregates (**Note**, **Card**, **DiscardedProposal**), one enforced invariant (the note is the source of truth for its cards — an unresolvable anchor rejects the card), and a two-handler outbox chain (`note_approved` → note-save → `note_saved` → flashcard-gen). The ADR `decision.md` formalized this shape on 2026-09-02; no `backend/src/domain/distill/` code exists yet.

## Findings

### Boundary and input contract

- Capture hands off via `note_approved` carrying a denormalized snapshot: `note_id`, `session_id`, `topic {id, label}`, `content`, `tags [{id, label}]`, `approved_at` — so distill never reaches into capture vocabulary stores.
- `note_approved` is distill's **only** input; notes are born only in capture. Remember opens capture mode rather than authoring notes.
- Distill's `Note.id` **is** capture's note id. Redelivery idempotency falls out of shared identity rather than a separate uniqueness rule.

### Three aggregates

**Note (distill)** — living knowledge artifact with content from the snapshot:

- Fields: `id`, `session_id`, `topic: TopicSnapshot`, `content`, `tags: list[TagSnapshot]`, `version` (pinned at `1`), `distillation_status`, `approved_at`, `created_at`.
- `topic` and `tags` are embedded value objects carrying label and source id, not references into capture vocabulary.
- **No immutability guard** on content — capture's `Note` is frozen post-approval (`_ensure_draft`); distill's note is deliberately mutable for future remember-driven amendments.
- `distillation_status`: `generating | ready | failed`. `ready` with zero cards is a **success** (not every note deserves flashcards).

**Card** — grounded flashcard, by construction:

- Fields: `id`, `note_id`, `note_version`, `question`, `answer`, `anchor: Anchor`, `status`, `created_at`.
- `status`: `active | rejected` — `rejected` exists but **nothing sets it in v1** (remember → distill command later).
- Carries **no scheduling state** — "never scheduled" is the default meaning of a new card for any spaced-repetition algorithm.

**DiscardedProposal** — rejected generation proposal, retained for observability:

- Fields: `id`, `note_id`, `question`, `answer`, `quote`, `reason`, `created_at`.
- Deliberately **not** a `Card` with a status — a card whose anchor does not resolve would violate the grounding invariant.

### The grounding invariant

- Every card carries an anchor into the note it came from. **An anchor that does not resolve rejects the card.**
- `Anchor` stores a **verbatim quote**; block position for "jump to this block" is derived at read time by the parser, not stored.
- Matching runs against the parser's **rendered block text** (whitespace collapsed, inline emphasis stripped), not raw markdown.
- An anchor must resolve **within a single block**; a quote spanning a paragraph boundary is rejected.
- A run that loses proposals to grounding is a **success with fewer cards**, not a failure. Rejection does not trigger automatic regeneration.

### Outbox chain (two handlers)

```
note_approved  →  [note-save]      →  persist Note  →  enqueue note_saved
note_saved     →  [flashcard-gen]  →  proposals → parser resolve → Card | DiscardedProposal
```

- Each handler runs in its **own** `UnitOfWork` with an `outbox` member (same pattern as capture).
- Idempotency: note-save on `note_id`; flashcard-gen on `(note_id, note_version)`.
- Notion publication is **deferred** — local record commits transactionally with the outbox; `notion_page_id` fills in a later publication step. `backend-stack`'s cross-store atomicity question is answered in two halves: single store now, separate publication step later.

### Ports

| Port | Direction | Role |
|------|-----------|------|
| Repository per aggregate | outbound | `Note`, `Card`, `DiscardedProposal` |
| `CardGeneration` | outbound | Note content in → proposals `{question, answer, quote}` out; InMemoryFirst deterministic generator before LLM |
| `NoteDocumentParser` | outbound | Markdown → blocks with rendered text (needed for rendering regardless of anchoring) |
| *(no scheduling port)* | — | FSRS belongs to remember; port must hide algorithm state model, not merely rename it |

### Ownership boundaries

| Artifact | Owner | Notes |
|----------|-------|-------|
| Note | Distill | Remember asks distill to amend; does not hold its own copy |
| Card content | Distill | `question`, `answer`, `note_id`, anchor |
| Card learning state | Remember (future) | Keyed by `card_id`; **lazy** wrap on first encounter |
| User card rejection | Remember → distill (command) | Negative signal for generation |
| Note birth | Capture only | `note_approved` is distill's sole input |

### Queries (DTOs, not TUI shell)

- **list notes** — id, topic label, tag labels, `distillation_status`, card count; ordered by update date across note and cards. Three "no cards" cases distinguishable: `generating`, `ready`+0, `failed`.
- **get note** — content plus cards' anchors resolved to block positions.
- **list cards for a note** — note-to-card binding addressed by **selection**, not by id.

### Naming

Capture's `Note` and distill's `Note` keep the same class name, disambiguated by module path (`domain/capture/` vs `domain/distill/`). Renaming capture's aggregate was rejected as churn.

### Duck → ADR arc (what changed between session and decision)

| Topic | Duck arc | ADR resolution |
|-------|----------|----------------|
| Status attachment | Run record argued, then withdrawn when remember/regen pushed out | `distillation_status` on **Note**; no `DistillationRun` aggregate |
| Fan-out shape | note-save ∥ flashcard-gen (Notion branch removed) | Two chained consumers with separate UoWs |
| Anchor form | Abstraction → verbatim quote | `Anchor` VO + parser matching rules |
| Discarded proposals | "Retain rejected" | Named third aggregate `DiscardedProposal` |
| Card ownership | OPEN at session end | ACCEPTED: distill content / remember learning state |

### Out of domain scope (duck only — TUI/shell)

Overlay over capture view, slash-command dispatcher, Zustand notification state, stable list ordering with state badge, one-time "cards ready" message, `/sessions` listability (capture-side). ADR defines query DTOs the shell reads but not Ink/Zustand/dispatcher behavior.

### Duck-only residue (not in ADR decision body)

- Provenance link: capture session opened from review → originating card.
- Internal endpoint for inspecting discarded proposals (wanted eventually, not now).
- Versioned snapshot mechanism for Notion drift (parked with Notion deferral; survives for internal mutability).

## Code References

- `context/duck-sessions/distill-pillar/log.md:1-49` — Current State: settled structural decisions
- `context/duck-sessions/distill-pillar/log.md:75-186` — Log entries: ACCEPTED domain-shape decisions
- `context/adrs/distill-domain-shape/adr.md:8` — `origin: distill-pillar` edge to duck session
- `context/adrs/distill-domain-shape/decision.md:27-109` — Formalized domain shape (aggregates, invariant, handlers, ports, queries)
- `context/duck-sessions/outbox-shared/log.md:10` — `note_approved` envelope payload shape
- `backend/src/domain/capture/note.py:23-75` — Capture `Note` aggregate (frozen post-approval)
- `backend/src/domain/capture/outbox.py:19-43` — `NoteApprovedPayload` construction
- `backend/src/application/capture/commands/approve_note.py:12-46` — Approve → outbox enqueue flow
- `context/foundation/project-overview.md` — Product filter: not every note deserves memorization
