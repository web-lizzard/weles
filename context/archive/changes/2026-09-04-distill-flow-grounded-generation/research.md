---
date: 2026-09-04T12:07:00+02:00
topic: "Distill domain required for grounded flashcard generation (S-02)"
topic_slug: null
container_id: distill-flow-grounded-generation
tags: [research, distill, domain-model, card-generation, grounding-invariant, outbox]
last_updated: 2026-09-04
---

# Research: Distill domain required for grounded flashcard generation (S-02)

## Research Question

Wydestyluj domene z @context/adrs/distill-domain-shape/adr.md wymaganą dla tej zmiany

## Summary

Slice S-01 (`distill-flow-note-lands`) delivered the distill `Note` aggregate, the save path, and the `note_saved` outbox envelope. Slice S-02 (`distill-flow-grounded-generation`) is effectively **greenfield on the card side**: the entire `Card` model, factory, policies, generation and parser ports, application command, and `flashcard-gen` handler must be built, while extending `Note` with `generating → ready | failed` transitions. Zero live cards is a success (`ready`), not a failure. The ADR at `context/adrs/distill-domain-shape/decision.md` is the authoritative source; `adr.md` is identity-only and `frame.md` is superseded input.

## Findings

### Current state (S-01 complete)

The distill bounded context today implements only the **note-save** half of the ADR's two-handler outbox chain:

- **`Note` aggregate** — passive snapshot with embedded `TopicSnapshot` / `TagSnapshot`, shared `NoteId` with capture, always minted in `generating` status (`backend/src/domain/distill/note.py:15-43`).
- **Note-side value objects** — `NoteId`, `SessionId`, `NoteContent`, `DistillationStatus` (`generating | ready | failed`) at `backend/src/domain/distill/value_objects.py:14-54`. Only `generating` is written today.
- **`NoteRepository`** — `add` / `get` at `backend/src/domain/distill/ports.py:7-10`.
- **`SaveNoteCommand`** — idempotent on `note_id`; persists note and enqueues `note_saved` (`backend/src/application/distill/commands/save_note.py`).
- **`SaveNoteHandler`** — adapter consuming `note_approved`, delegating to the command (`backend/src/adapters/out/worker/handlers/note_save.py`).
- **`UnitOfWork`** — `notes` + `outbox` only (`backend/src/application/distill/ports.py:7-15`).

No `Card` aggregate, `CardRepository`, `CardFactory`, `CardGeneration` port, `NoteDocumentParser`, or `FlashcardGenHandler` exists yet. `compose.py` registers only `SaveNoteHandler`.

### ADR domain shape for S-02

Per `context/adrs/distill-domain-shape/decision.md`, distill owns: consume an approved note, hold it, generate grounded cards from it. Two aggregates:

**Note** (extend existing):

- Fields already match ADR (`id`, `session_id`, `topic`, `content`, `tags`, `distillation_status`, `approved_at`, `created_at`).
- Add `mark_ready(note)` / `mark_failed(note)` transitions.
- `ready` with zero live cards is success (`decision.md:32`).
- No immutability guard — distill's note is a living artifact, unlike capture's frozen post-approval note.

**Card** (new):

- `id`, `note_id`, `front: CardSide`, `back: CardSide`, `anchor: Anchor`, `discard: Discard | None`, `created_at` (`decision.md:34-42`).
- `front`/`back` not `question`/`answer` — flashcards are not always rhetorical questions.
- Invariant: the two sides must differ after canonicalization.
- `discard: Discard | None` is the sole removal mechanism — no separate `status` field. Live card ⇔ `discard is None`.
- No scheduling state on `Card` (remember's concern).

**Value objects to add:**

| VO | Rules |
|----|-------|
| `CardId` | UUID wrapper |
| `CardSide` | strip, non-empty, absolute max bound at construction |
| `Anchor` | verbatim quote from the note |
| `Discard` | `reason`, `detail`, `discarded_at` |
| `DiscardReason` | `ungrounded`, `oversized`, `user_audit` |
| `CardLengthPolicy` | `front_max`, `back_max` — applied at mint time only, not on reconstitution |

**Exceptions to add** (`CoreException` subclasses): `EmptyCardSideError`, `CardSideTooLongError`, `IdenticalCardSidesError` — each needs an HTTP mapping entry.

### Grounding invariant

Every live card carries an anchor into the note it came from (`decision.md:44-48`):

1. **Application** resolves each proposal's quote through `NoteDocumentParser`.
2. **Domain** (`CardFactory`) judges the outcome: live card or `Discard(ungrounded)`.
3. Ungrounded proposals are **persisted as discarded cards** (FR-006), not dropped silently.
4. Fewer live cards than proposals is success — no automatic regeneration.

Structurally invalid proposals (empty side, over absolute `CardSide` bound, identical sides) never become cards and leave **no discarded row** (`decision.md:126`).

### CardFactory and policies

`CardFactory` is the single minting door (`decision.md:60-67`). Evaluation order is fixed:

1. **Grounding first** — not in the configurable policy collection; a fabricated card must not hide behind a verbosity signal.
2. **`CardLengthPolicy`** — breach mints `Discard(oversized)` with `detail` naming which side and which bound.
3. **First violation wins** — one `Discard` per card.

`CardSide` defines what a side **is** (construction invariant). `CardLengthPolicy` defines what a side **should be** (quality judgement at mint time).

### Outbox chain

| Envelope | Handler | Status |
|----------|---------|--------|
| `note_approved` | `SaveNoteHandler` | Done (S-01) |
| `note_saved` | `FlashcardGenHandler` | Missing (S-02) |

Both handlers idempotent on `note_id`: flashcard-gen no-ops when `distillation_status` has left `generating` (`decision.md:92`). No outbound envelope after generation — remember wraps cards lazily (`decision.md:110`).

### Ports

| Port | Layer | S-02 action |
|------|-------|-------------|
| `NoteRepository` | domain | Exists; needs update path for status transitions |
| `CardRepository` | domain | Add — `add`, optionally `list_by_note` |
| `CardGeneration` | application outbound | Add — `NoteContent` in, proposals `{front, back, quote}` out |
| `NoteDocumentParser` | application outbound | Add — markdown to blocks, quote resolution |
| `UnitOfWork.cards` | application | Extend existing `UnitOfWork` |

InMemoryFirst: deterministic `CardGeneration` adapter (mirror capture's `reply_generation`) before wiring a model.

### Application command

`GenerateCardsCommand` (name TBD) orchestrates:

1. Load note; no-op if missing or `distillation_status != generating`.
2. Call `CardGeneration.generate(note.content)`.
3. For each proposal: resolve quote via parser, mint via `CardFactory`, persist if not `None`.
4. Set `mark_ready(note)` on success (regardless of live card count) or `mark_failed(note)` on failure.
5. Commit inside `UnitOfWork` — no new outbox envelope.

Handler is an adapter implementing `OutboxHandler`; no distill logic lives under `adapters/` beyond delegation (`decision.md:101`).

### Acceptance criteria mapping

| AC | Requirement | Domain / application element |
|----|-------------|------------------------------|
| AC-03 | Cards exist without user asking | `FlashcardGenHandler` + `CardGeneration` |
| AC-04 | Zero cards = completed state | `mark_ready()` regardless of live card count |
| AC-05 | Every visible card quotes a note fragment | `Anchor` on every live card (`discard is None`) |
| AC-06 | Ungrounded proposals never reach user | `CardFactory` → `Discard(ungrounded)` |

### Suggested file layout

```
domain/distill/
  card.py
  card_factory.py
  value_objects.py      # extend
  exceptions.py         # extend
  ports.py              # + CardRepository
  note.py               # + mark_ready, mark_failed

application/distill/
  commands/generate_cards.py
  ports.py              # + CardGeneration, NoteDocumentParser, UoW.cards

adapters/out/in_memory/distill/
  card_repository.py
  card_generation.py
  note_document_parser.py
  unit_of_work.py       # + cards

adapters/out/worker/handlers/
  flashcard_gen.py
```

### Patterns to follow from existing code

- **Frozen VOs with strip-on-input** — mirror `NoteContent` at `backend/src/domain/distill/value_objects.py:32-48` and capture conventions.
- **Module-level factory** — `mint_note()` pattern, not classmethod on aggregate.
- **Command owns commit boundary** — mirror `SaveNoteCommand` idempotency pattern.
- **Outbox handler = adapter** — validate envelope, delegate to command; malformed envelope logs and acks without retry.
- **`uow_factory` injection** — distill commands use factory (not UoW instance) because handlers create a fresh UoW per delivery.
- **Contract tests** — parametrize `CardRepository` and `CardGeneration` like `test_note_repository_contract.py`.

### Explicitly out of S-02 scope

- Query DTOs, note list, note detail (S-03, S-04) — `decision.md:116`
- `DiscardCard` command / `user_audit` caller — VO exists in ADR; command is future work
- Quote-matching algorithm — adapter concern in `NoteDocumentParser` implementation
- `cards_generated` envelope
- Rejected-proposal inspection UI — rows retained (FR-006), no reader yet (`stories.md:83-85`)

## Code References

- `context/adrs/distill-domain-shape/decision.md:27-112` — authoritative domain shape, ports, boundary rules, outbox chain
- `context/adrs/distill-domain-shape/frame.md` — superseded first pass; input only, not a decision
- `context/efforts/distill-flow/roadmap.md:38-44` — S-02 slice definition and AC-03–06
- `context/efforts/distill-flow/stories.md:21-37` — US-02, US-03 acceptance criteria
- `context/efforts/distill-flow/prd.md:44-48` — FR-002–FR-006 functional requirements
- `backend/src/domain/distill/note.py:15-43` — existing `Note` aggregate and `mint_note`
- `backend/src/domain/distill/value_objects.py:14-54` — note VOs and `DistillationStatus`
- `backend/src/domain/distill/ports.py:7-10` — `NoteRepository`
- `backend/src/domain/distill/outbox.py:7-14` — `NOTE_SAVED` envelope (S-02 trigger)
- `backend/src/application/distill/commands/save_note.py` — idempotent save + enqueue pattern
- `backend/src/application/distill/ports.py:7-15` — distill `UnitOfWork` (notes + outbox only)
- `backend/src/adapters/out/worker/handlers/note_save.py` — outbox handler adapter pattern
- `backend/src/application/shared/outbox/ports.py:6-9` — `OutboxHandler` protocol
- `backend/src/domain/shared/outbox/model.py:29-84` — envelope model and lifecycle
- `backend/tests/unit/distill/test_save_note_command.py` — idempotency and `note_saved` enqueue tests
- `backend/tests/unit/distill/contracts/test_note_repository_contract.py` — port contract test pattern

## Open Questions

1. **Quote-matching rule** — how a cited fragment is compared against note content so honest cards are not rejected over formatting alone. PRD Open Question 2; resolved at `/plan`, not in domain.
2. **`user_audit` without a caller** — ADR includes `DiscardReason.user_audit` for manual card removal; PRD Non-Goals removed manual curation from this ship. ADR is `open`; amendment is the route if the VO should be deferred.
3. **Note stranded in `generating`** — after outbox `max_attempts`, the envelope goes to `failed` but nothing moves the note's `distillation_status`. ADR records this as an accepted cost (`decision.md:134`).
