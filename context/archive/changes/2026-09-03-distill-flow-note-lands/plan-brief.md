# Note Lands in Distill — Plan Brief

> Full plan: `plan.md`

## What & Why

Right now an approved capture note produces a `note_approved` outbox envelope that only a logging stub consumes — distill holds nothing. This slice (`distill-flow` S-01, AC-01/AC-02) gives that envelope a real handler: it persists distill's own `Note` aggregate in `generating` status and enqueues `note_saved` for S-02's flashcard-gen to consume later.

## Starting Point

`domain/distill/` and `application/distill/` don't exist. Capture already atomically enqueues `note_approved` on approval; the shared in-memory outbox store, `OutboxWorker`, and `OutboxHandler` protocol are built and proven by capture's own handler chain. `LoggingNoteSaveHandler` validates the payload and logs it, persisting nothing.

## Desired End State

An approved note lands in distill with zero user action, exactly once however many times its approval envelope is redelivered. A malformed envelope is logged, not retried forever.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Inbound payload validation | Reuse capture's `NoteApprovedPayload`, adapter layer only | ADR's boundary rule targets domain/application imports, not a shared DTO at the adapter; avoids a duplicate hand-maintained shape | Plan |
| `note_saved` payload | `note_id` only | S-02 reads the note back via `NoteRepository.get`; a richer payload duplicates data this slice doesn't need | Plan |
| `UnitOfWork` port scope | `notes` + `outbox` only | Names only what this slice's code calls; `cards` joins when S-02 plans it, not as an unused stub today | Plan |
| Note construction | Standalone `mint_note` function, not a `Note` classmethod | Keeps both the aggregate and the factory ignorant of the outbox payload shape — the user's explicit call | Plan |
| Malformed envelope | Handler catches, logs, acks (no retry) | A shape defect isn't fixed by retrying; avoids burning `max_attempts` on something that can never resolve | Plan |
| Idempotent redelivery | Distinct no-op log line | Makes at-least-once redelivery visible in logs instead of indistinguishable from a first save | Plan |
| `SaveNoteCommand` construction | `UnitOfWork` **factory**, not a shared instance | The command is a long-lived singleton but `OutboxWorker` dispatches concurrently; one shared `UnitOfWork` would race two envelopes' snapshot/restore | Plan |

## Scope

**In scope:** `domain/distill/` (Note, VOs, exceptions, `mint_note`, `NoteRepository` port, `note_saved` envelope), `application/distill/` (`UnitOfWork` port, `SaveNoteCommand`), the in-memory adapters for both, the real `SaveNoteHandler` replacing the logging stub, and `compose.py` wiring.

**Out of scope:** Card generation and everything `CardFactory`/`CardRepository`-shaped (S-02); `distillation_status` reaching `ready`/`failed`; any note list/detail read surface (S-03, S-04); anchor jump (S-05); Notion publication; note amendment.

## Architecture / Approach

Two-handler outbox chain per the ADR: `note_approved → [note-save] → note_saved → [flashcard-gen]`. This slice builds only the first handler. The adapter is the sole place capture's `NoteApprovedPayload` is imported; it unpacks the payload into distill's own value objects before calling the application command, so `application/distill/` never names a capture type. Idempotency falls out of checking `NoteRepository.get(note_id)` before minting — the same id capture's note already carries, never a new one.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Note domain model — stubs | `Note`, VOs, exceptions, `mint_note` signature | — |
| 2. Note domain model — behavior | `NoteContent` validation, `mint_note` mapping, tests | — |
| 3. NoteRepository — stubs | Port + in-memory adapter skeleton | — |
| 4. NoteRepository — behavior | Adapter implementation + contract test | — |
| 5. Application layer & envelope — stubs | `UnitOfWork` port + adapter, `note_saved` type, `SaveNoteCommand` skeleton | Getting the `UnitOfWork`-factory shape right before behavior lands |
| 6. SaveNoteCommand — behavior | Idempotent save + enqueue + tests | Idempotency check must run before minting, not after |
| 7. Handler adapter — stubs | `SaveNoteHandler` added alongside the stub | — |
| 8. Handler adapter — behavior | Payload unpack/dispatch + malformed-payload path + tests | Must not let a capture type leak past the adapter |
| 9. Composition | Wiring, shared outbox store, stub deletion | Reusing capture's exact `_outbox_store`/`_outbox_appender` instances |

**Prerequisites:** None — capture's outbox chain and shared infrastructure already exist.
**Estimated effort:** 9 phases, each a small, single-concern change; no new external dependencies.

## Open Risks & Assumptions

- A note can be stranded in `generating` forever if `flashcard-gen` (S-02) never runs — inherited from the ADR's own accepted consequence, not new to this slice.
- The manual verification step relies on the existing `/_outbox` debug endpoint; there's still no way to see a distill note itself until S-03/S-04 add a read surface.

## Success Criteria (Summary)

- An approved note is persisted as a distill `Note` in `generating` status with no user action.
- Redelivering the same `note_approved` envelope leaves exactly one note and one `note_saved` envelope.
- A malformed envelope is logged and acknowledged, never retried indefinitely.
