---
date: 2026-09-03T17:29:00+02:00
topic: "Domain model requirements for the note-save slice (S-01)"
topic_slug: null
container_id: distill-flow-note-lands
tags: [research, distill, note-save, outbox, domain-model]
last_updated: 2026-09-03
---

# Research: Domain model requirements for the note-save slice (S-01)

## Research Question

/research distill-flow-note-lands wydestyuj mi wymagania co do modelu domownego dla tego slice'a z @context/adrs/distill-domain-shape/decision.md

## Summary

Slice S-01 (`distill-flow-note-lands`) implements only AC-01 and AC-02: an approved capture note is held by Weles automatically, exactly once on redelivery. The domain model for this slice is the distill **Note** aggregate, its embedded snapshot value objects, a **NoteRepository** port, and the outbound **`note_saved`** envelope — wired through a note-save command that consumes `note_approved` and persists in `generating` status. The **Card** aggregate, **CardFactory**, generation ports, and flashcard-gen handler belong to S-02. No `domain/distill/` or `application/distill/` code exists yet; capture already produces the denormalized `note_approved` envelope and a logging stub handler consumes it without persisting anything.

## Findings

### Slice scope (S-01 vs later slices)

S-01 covers FR-001 / AC-01–AC-02 only (`context/efforts/distill-flow/roadmap.md:31-36`, `stories.md:12-19`): after approval with no further user action, the note is held by Weles; one approved note is held exactly once on redelivery. Card generation (AC-03–AC-06), note list/detail UI (AC-07–AC-13), and anchor jump (AC-13) are deferred to S-02 through S-05.

The ADR defines a two-handler outbox chain (`decision.md:84-92`):

```
note_approved → [note-save]  → persist Note (generating) → enqueue note_saved
note_saved    → [flashcard-gen] → cards + status → ready|failed
```

S-01 owns the note-save half. S-02 owns flashcard-gen.

### Note aggregate — fields and rules

Per `decision.md:27-33`, the distill **Note** aggregate carries:

| Field | Requirement |
| --- | --- |
| `id` | Same UUID as the capture note — not a new id. Redelivery idempotency falls out of shared identity (`decision.md:29`). |
| `session_id` | From envelope payload. |
| `topic` | Embedded `TopicSnapshot` with `id` + `label` — never a reference into capture vocabulary. |
| `content` | Meaningful string as a value object (capture uses `NoteContent` with strip and bounds). |
| `tags` | `list[TagSnapshot]` — embedded `{id, label}` snapshots, not capture tag ids. |
| `distillation_status` | `generating \| ready \| failed`. S-01 sets `generating` only; transitions to `ready`/`failed` are S-02. |
| `approved_at` | Carried from envelope payload. |
| `created_at` | UTC timestamp set at save time in distill. |

Behavioral rules:

- **No immutability guard.** Capture's `Note` freezes after approval via `_ensure_draft` (`domain/capture/note.py:51-79`). Distill's note is deliberately mutable so amendment can land later (`decision.md:31`).
- **`ready` with zero cards is success** — but S-01 never reaches `ready` (`decision.md:32-33`).
- **No `version` field** — cut from ADR as dead data (`decision.md:151`).

Factory: `Note.from_approved_payload(...)` maps the denormalized envelope snapshot onto the aggregate, setting `distillation_status=generating` and stamping `created_at` in UTC.

### Value objects

| VO | Shape | Notes |
| --- | --- | --- |
| `TopicSnapshot` | `frozen=True`, `id: UUID`, `label: str` | Same shape as capture's `VocabularySnapshot` (`domain/capture/outbox.py:14-17`) but named per ADR. |
| `TagSnapshot` | Same as `TopicSnapshot` | One per tag in the envelope. |
| `NoteId` | `frozen=True`, wrapper on `UUID` | Value from payload `note_id`, not `.new()`. |
| `NoteContent` (or equivalent) | `frozen=True`, strip + non-empty + bound | Follow capture convention (`domain/capture/value_objects.py:153-169`). |
| `DistillationStatus` | `StrEnum`: `generating`, `ready`, `failed` | S-01 uses `generating` only. |

### ADR elements in scope for S-01

| Element | ADR ref | S-01 role |
| --- | --- | --- |
| Note aggregate | `decision.md:27-32` | Persist from envelope; status `generating`. |
| TopicSnapshot / TagSnapshot | `decision.md:30-31` | Embedded from denormalized payload. |
| NoteRepository | `decision.md:96` | `add` + `get` by note id. |
| UnitOfWork (distill) | `decision.md:99` | `notes` + `outbox`; handler never holds two modules' UoWs. |
| note-save handler | `decision.md:85-86`, `101` | `OutboxHandler` adapter → application command. |
| `note_saved` envelope | `decision.md:85-86` | Produced in same transaction as note persist. |
| Idempotency on `note_id` | `decision.md:92` | No-op when note exists; no second `note_saved`. |
| Boundary rules | `decision.md:106-107` | No imports from `domain/capture/` or `application/capture/`. |

### ADR elements deferred beyond S-01

| Element | Deferred to |
| --- | --- |
| Card aggregate, CardSide, Anchor, Discard, DiscardReason | S-02 (`decision.md:34-43`, `69-80`) |
| CardFactory, CardLengthPolicy, grounding invariant | S-02 (`decision.md:44-67`) |
| CardRepository | S-02 (`decision.md:96`) |
| flashcard-gen handler | S-02 (`decision.md:86-87`) |
| CardGeneration, NoteDocumentParser ports | S-02 (`decision.md:97-98`) |
| `distillation_status` → `ready` / `failed` | S-02 (`decision.md:32`, `86-87`) |
| UoW `cards` member | S-02 (`decision.md:99`) |
| Query DTOs, list ordering | S-03+ (`decision.md:116`, `162`) |
| DiscardCard / `user_audit` | Review surface (`decision.md:77`) |
| Quote-matching algorithm | Adapter concern (`decision.md:40`, `116`) |

### Ports and UnitOfWork

**NoteRepository** (`domain/distill/ports.py`) — mirror capture shape (`domain/capture/ports.py:22-26`):

```python
async def add(self, note: Note) -> None
async def get(self, note_id: NoteId) -> Note | None
```

Contract tests parametrize over implementations; second `add` with same id overwrites (`test_note_repository_contract.py:78-91`). In-memory adapter uses `dict[UUID, T]` keyed by id VO's `.value` with `snapshot()` / `restore()` for UoW rollback.

**UnitOfWork** (`application/distill/ports.py`) — mirror capture (`application/capture/ports.py:39-52`):

```python
class UnitOfWork(Protocol):
    notes: NoteRepository
    outbox: OutboxAppender  # domain port from shared/outbox
    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, *exc: object) -> None: ...
    async def commit(self) -> None: ...
```

Every mutating command uses `async with uow` + explicit `commit()` (`application/capture/commands/approve_note.py:16-44`). In-memory implementation snapshots all backing stores on enter and restores on exit without commit (`adapters/out/in_memory/capture/unit_of_work.py:64-84`).

### Outbox — inbound and outbound

**Inbound: `note_approved@1`**

Payload fields (`domain/capture/outbox.py:19-40`):

| Field | Type |
| --- | --- |
| `note_id` | UUID |
| `session_id` | UUID |
| `topic` | `{id, label}` |
| `content` | str |
| `tags` | `[{id, label}]` |
| `approved_at` | datetime |

Produced atomically with approval (`application/capture/commands/approve_note.py:32-44`). Labels resolved at approve time via `note_vocabulary.resolve(note)`, not lazily at consume time.

**Outbound: `note_saved`**

New type in `domain/distill/outbox.py`, following the frozen payload + `to_envelope()` pattern (`domain/capture/outbox.py:42-43`). Minimum payload: `note_id` (for flashcard-gen in S-02). Enqueued in the same transaction as note persist (`decision.md:85-86`).

**Handler wiring**

`OutboxHandler` protocol (`application/shared/outbox/ports.py:6-9`) requires `envelope_type` + `async handle(envelope)`. Current stub validates with `NoteApprovedPayload.model_validate` and logs (`adapters/out/worker/handlers/note_save.py:9-18`). S-01 replaces this with a handler that delegates to a `SaveNoteCommand` using distill's own UoW. Registered in `adapters/compose.py:63-70`.

### Idempotency (AC-02)

At-least-once delivery requires note-save to be idempotent on `note_id` (`decision.md:92`):

```python
existing = await uow.notes.get(NoteId(value=payload.note_id))
if existing is not None:
    return  # no second note_saved
note = Note.from_approved_payload(payload)
await uow.notes.add(note)
await uow.outbox.append(note_saved_payload.to_envelope())
await uow.commit()
```

Capture itself has no explicit idempotency checks; distill must implement this guard because redelivery is expected.

### Boundary rules

From `decision.md:106-112`, checkable for S-01:

- `domain/distill/` and `application/distill/` import nothing from `domain/capture/` or `application/capture/`. The envelope payload is the sole inbound channel.
- Notes are born only in capture; distill consumes them.
- No scheduling state on any field.
- Distill emits no "cards generated" envelope.

The adapter may validate inbound payload via capture's `NoteApprovedPayload` Pydantic model (as the stub does) without importing capture domain aggregates — boundary is on domain/application imports, not on shared frozen DTO shapes in the adapter layer.

### Existing code and gaps

**Exists today:**

- `NoteApprovedPayload` producer (`domain/capture/outbox.py:11-43`)
- `ApproveNoteCommand` with atomic envelope append (`application/capture/commands/approve_note.py:16-44`)
- Shared outbox infrastructure: `OutboxEnvelope`, `OutboxHandler`, `OutboxWorker` (`domain/shared/outbox/`, `application/shared/outbox/`, `adapters/out/worker/`)
- `LoggingNoteSaveHandler` stub (`adapters/out/worker/handlers/note_save.py:9-18`)
- Composition root wiring (`adapters/compose.py:59-70`)

**Must be built for S-01:**

1. `domain/distill/` — Note aggregate, snapshot VOs, DistillationStatus, NoteRepository port, exceptions, `note_saved` outbox type
2. `application/distill/` — UnitOfWork protocol, SaveNoteCommand with idempotency
3. `adapters/out/in_memory/distill/` — InMemoryNoteRepository, InMemoryUnitOfWork (sharing InMemoryOutboxStore with capture)
4. Real note-save handler replacing logging stub
5. `compose.py` wiring for distill repos, UoW factory, handler registration
6. Unit tests: Note factory from payload, idempotent save, `note_saved` enqueued once; contract test for NoteRepository

## Code References

- `context/adrs/distill-domain-shape/decision.md:27-33` — Note aggregate fields and distillation_status rules
- `context/adrs/distill-domain-shape/decision.md:84-92` — two-handler outbox chain and idempotency
- `context/adrs/distill-domain-shape/decision.md:96-101` — ports and handler adapter pattern
- `context/adrs/distill-domain-shape/decision.md:106-107` — boundary rules (no capture imports)
- `context/efforts/distill-flow/roadmap.md:31-36` — S-01 scope and acceptance criteria
- `context/efforts/distill-flow/stories.md:12-19` — US-01 and AC-01, AC-02
- `backend/src/domain/capture/outbox.py:11-43` — NoteApprovedPayload shape and to_envelope()
- `backend/src/application/capture/commands/approve_note.py:16-44` — atomic approval + envelope append
- `backend/src/domain/capture/note.py:22-79` — capture Note (contrast: draft guard, topic_id/tag_ids)
- `backend/src/domain/capture/value_objects.py:153-169` — NoteContent VO pattern
- `backend/src/domain/capture/ports.py:22-26` — NoteRepository port shape
- `backend/src/application/capture/ports.py:39-52` — UnitOfWork protocol shape
- `backend/src/application/shared/outbox/ports.py:6-9` — OutboxHandler protocol
- `backend/src/adapters/out/worker/handlers/note_save.py:9-18` — current logging stub handler
- `backend/src/adapters/compose.py:59-70` — outbox worker and handler registration
- `backend/src/adapters/out/in_memory/capture/unit_of_work.py:64-84` — snapshot/restore UoW pattern
- `backend/tests/unit/capture/test_note_repository_contract.py:78-91` — repository overwrite semantics

## Open Questions

- **Inbound DTO ownership.** The stub handler imports capture's `NoteApprovedPayload` for validation (`note_save.py:3,13`). Acceptable at the adapter layer, or should distill define a mirror struct to keep the adapter free of capture imports entirely?
- **`NoteSavedPayload` field set.** ADR mandates the envelope type but does not enumerate fields. Minimum is `note_id`; a fuller snapshot may simplify S-02 flashcard-gen.
- **Shared outbox store.** Distill's InMemoryUnitOfWork must share the same `InMemoryOutboxStore` instance as capture so envelopes enqueued on approve are visible to the worker.
