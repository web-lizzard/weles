---
date: 2026-08-30T15:55:38+00:00
topic: "Domain model requirements from linked ADRs for capture-flow-socratic-conversation (S-01)"
topic_slug: null
container_id: capture-flow-socratic-conversation
tags: [research, domain-model, capture-flow, capture-session, message, hexagonal-architecture]
last_updated: 2026-08-30
---

# Research: Domain model requirements from linked ADRs for capture-flow-socratic-conversation (S-01)

## Research Question

syntezuj wymagania odnośnie modelu domeny które muszą wejśc w tej zmianie, opieraj sie na podpietych adrach

## Summary

This change (`capture-flow-socratic-conversation`) realizes slice S-01 — AC-01 through AC-04, i.e. US-01's "start a session, have the agent probe understanding through follow-ups." Of the five aggregates `capture-flow-domain-shape` decides for the whole capture-flow domain, S-01 needs exactly **two**: `CaptureSession` (only its `start(topic)` factory and `open` status) and `Message` (only its `record(session_id, role, content)` factory, append-only). `Note`, `Topic`, and `Tag` — and `CaptureSession`'s `draft_note`/`approve`/`close` methods — belong to later slices (S-04, S-05, S-06 per the roadmap dependency chain) and are out of scope for this change's plan, even though the ADR settles their shape as part of one aggregate design.

`hexagonal-arch-shape` additionally constrains *how* these two aggregates must be built: pure domain layer with zero imports from application/adapters, one repository-style port per aggregate, in-memory adapter first, cross-aggregate references by id only, and no domain-owned transaction/commit notion. Message ordering and transcript assembly are explicitly pushed out of the domain layer — ordering to the persistence adapter, transcript assembly to an application-layer query (CQRS-lite), not a domain method.

Two things the ADR is explicit about **staying out** of the domain model for this slice: the agent's tool-call/probing mechanics (US-01) are not persisted at all, and `CaptureSession.topic` is a raw user-input string that deliberately does *not* participate in the `Topic` vocabulary/reconciliation mechanism — that only applies to the note-level topic at draft time (S-04).

## Findings

### CaptureSession — scoped to `start()` for this change

- Full aggregate shape: `id`, `topic: str`, `status` (`open`|`closed`), `created_at`, with `start(topic) -> CaptureSession` (class-level factory), `draft_note(...)`, `approve(note)`, `close()`. — `context/adrs/capture-flow-domain-shape/decision.md:21-27`
- Only `start(topic: str)` is exercised by this slice: AC-01 ("user can start a capture session by naming a topic") maps directly to it. — `context/efforts/capture-flow/stories.md:18`, `context/efforts/capture-flow/prd.md:39`
- `draft_note`, `approve`, `close` are declared by the ADR as part of the same class but are exercised by S-04 (draft) and S-06 (approve/close) per the roadmap's dependency chain `S-01 → S-02 → S-04 → S-05/S-06`. — `context/efforts/capture-flow/roadmap.md:20-27`, `:56-80`
- `CaptureSession.topic` is explicitly the raw label from AC-01, "not vocabulary — it deliberately does not participate in the reuse mechanism, because at session start there is nothing yet to reconcile against." No `Topic` aggregate is needed to satisfy this change. — `context/adrs/capture-flow-domain-shape/decision.md:28`
- Session stays `open` for the whole duration of this slice — nothing in S-01's ACs closes it, so the `closed` transition is never exercised here even though the field exists in the shape.

### Message — required in full for this change

- Full shape: `id`, `session_id`, `role` (`user`|`agent`), `content`, `created_at`; one factory `record(session_id, role, content)`; immutable, append-only, no mutators; `role` is a closed two-value set. — `context/adrs/capture-flow-domain-shape/decision.md:30-32`
- Directly required: AC-02 ("the agent asks follow-up questions in response to what the user says, rather than only recording it") and AC-04 (follow-ups target flagged-shaky parts) both depend on a persisted, readable conversation history that the agent turn re-reads. — `context/efforts/capture-flow/stories.md:19,21`
- No domain-computed sequence number — ordering is a persistence-adapter concern (insertion order / `created_at`, tie-broken at adapter level), so the domain model carries no ordering logic itself. — `context/adrs/capture-flow-domain-shape/decision.md:32`
- Assembling the transcript for the next agent turn is explicitly named a **query**, not a domain/write-path concern: "a dedicated query port reads a session's messages straight into DTOs, per hexagonal-arch-shape's CQRS-lite split." This change's plan therefore needs an application-layer query (transcript-by-session) alongside the `Message` domain type, not a domain method. — `context/adrs/capture-flow-domain-shape/decision.md:32`

### Explicitly excluded from this change's domain model

- **Tool-call mechanics** the agent runs while probing understanding (US-01) "stay out of the domain model entirely; no story asks for them to be persisted." — `context/adrs/capture-flow-domain-shape/decision.md:30`
- **`Note`** (topic_id, content, tag_ids, status, draft/approve/mutators) — needed starting S-04 (drafting) and S-06 (approve), not S-01. — `context/adrs/capture-flow-domain-shape/decision.md:34-44`, `context/efforts/capture-flow/roadmap.md:56-80`
- **`Topic`** and **`Tag`** vocabulary aggregates (id, label, embedding, `mint()`) and their reconciliation ports — needed starting S-04/S-05 (topic crystallization, dedup), not S-01. — `context/adrs/capture-flow-domain-shape/decision.md:46-50`, `context/efforts/capture-flow/roadmap.md:56-70`
- **Outbox envelope writing** (`ApproveNote` handler) — belongs to S-06 (approval), not S-01. — `context/adrs/capture-flow-domain-shape/decision.md:54`, `context/efforts/capture-flow/roadmap.md:73-80`

### Structural constraints from `hexagonal-arch-shape` (uses) that bind these two aggregates

- Domain layer has zero imports from application or adapters; no notion of transactions, HTTP, or storage technology; may be written as Pydantic `BaseModel`. `CaptureSession` and `Message` must not import FastAPI/SQLAlchemy/pydantic-ai etc. — `context/adrs/hexagonal-arch-shape/decision.md:16-18`
- Each aggregate is its own root with its own repository-style port; cross-aggregate references are by id, never by held object — `Message.session_id` is the concrete instance of this rule for this change. — `context/adrs/capture-flow-domain-shape/decision.md:19`, `context/adrs/hexagonal-arch-shape/decision.md:18`
- **InMemoryFirst**: every port (so, both `CaptureSession`'s and `Message`'s repository ports) gets an in-memory adapter before any I/O-bound one; behavior is proven against it first. — `context/adrs/hexagonal-arch-shape/decision.md:31`
- **Contract testing**: each of the two ports needs one behavioral contract-test suite, parametrized over adapters; the in-memory implementation runs it on every CI invocation. — `context/adrs/hexagonal-arch-shape/decision.md:33`
- **CQRS-lite / UnitOfWork**: the commit boundary is application-owned (`UnitOfWork` port), never a domain concern — `CaptureSession.start()` and `Message.record()` themselves carry no commit/transaction logic; that's the command handler's job in this change's application layer. — `context/adrs/hexagonal-arch-shape/decision.md:20-23`
- **Exception mapping**: any exception `CaptureSession`/`Message` domain code raises must descend from `CoreException`, deriving a `code` via snake_case from the class name (override only when needed); the input adapter owns the `code → transport error` mapping and never imports the concrete exception class. — `context/adrs/hexagonal-arch-shape/decision.md:67`

## Code References

- `context/changes/capture-flow-socratic-conversation/change.md:9-13` — `adr_refs` linking this change to `capture-flow-domain-shape` (implements) and `hexagonal-arch-shape` (uses)
- `context/adrs/capture-flow-domain-shape/decision.md:19-27` — `CaptureSession` aggregate shape and methods
- `context/adrs/capture-flow-domain-shape/decision.md:28` — `CaptureSession.topic` deliberately excluded from vocabulary reconciliation
- `context/adrs/capture-flow-domain-shape/decision.md:30-32` — `Message` aggregate shape, append-only, transcript-as-query
- `context/adrs/capture-flow-domain-shape/decision.md:34-44` — `Note` aggregate shape (out of scope for this change)
- `context/adrs/capture-flow-domain-shape/decision.md:46-50` — `Topic`/`Tag` vocabulary aggregates and reconciliation mechanism (out of scope for this change)
- `context/adrs/capture-flow-domain-shape/decision.md:54` — outbox envelope written by `ApproveNote` handler (out of scope for this change)
- `context/adrs/hexagonal-arch-shape/decision.md:16-18` — layering rules and domain-layer import constraints
- `context/adrs/hexagonal-arch-shape/decision.md:20-23` — CQRS-lite command/query split and `UnitOfWork` ownership
- `context/adrs/hexagonal-arch-shape/decision.md:31` — InMemoryFirst rule
- `context/adrs/hexagonal-arch-shape/decision.md:33` — contract-testing rule
- `context/adrs/hexagonal-arch-shape/decision.md:67` — `CoreException`/`code` exception-mapping rule
- `context/efforts/capture-flow/prd.md:39-41` — FR-001, FR-002, FR-003
- `context/efforts/capture-flow/stories.md:12-21` — US-01, AC-01–AC-04
- `context/efforts/capture-flow/roadmap.md:20-27` — slice dependency graph (`S-01 → S-02 → S-04 → S-05/S-06`)
- `context/efforts/capture-flow/roadmap.md:31-80` — per-slice AC assignment (S-01 through S-06)

## Open Questions

- Whether this change's `CaptureSession` class should be implemented with only `start()` now, or with the full ADR-decided shape (`draft_note`/`approve`/`close` stubbed but unused) landing in this change and only *exercised* later — the ADR settles the aggregate as one design, but slice-vs-implementation boundary is a `/plan` call, not something either ADR resolves.
- No validation rule is specified for `CaptureSession.topic` / message `content` (e.g. non-empty) — left to `/plan`.
- The application-layer query DTO/port for "transcript by session" (needed by AC-02/AC-04) is named by `capture-flow-domain-shape` but not designed — shape is `/plan`'s to decide, per `hexagonal-arch-shape`'s DTO-boundary rule.
