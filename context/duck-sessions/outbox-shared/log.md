## Current State

The outbox shape needed to unblock `capture-flow-review-approve-outbox` (S-06) is settled. Three domain modules share it conceptually — **capture**, **distill**, **remember** (product-loop-shaped, not process-shaped) — though only `capture` (producer) and `distill`'s two processes (note-save, flashcard-gen — consumers) are confirmed outbox participants; `remember`'s relationship to it is unresolved and parked.

**Settled shape:**
- **Location:** `domain.shared.outbox.model` (generic `OutboxEnvelope`) and `domain.shared.outbox.ports` (`OutboxRepository`). `domain/shared/` is a general-purpose bucket for future cross-context abstractions (e.g. LLM-instruction value objects), organized as sub-packages per concern — `outbox` is its first tenant, not its only one. Extends `hexagonal-arch-shape`'s directory convention, which has no shared bucket today — needs an ADR amendment once implemented.
- **Atomicity:** outbox enqueue is a member of the **producer's own `UnitOfWork`** (`uow.outbox.enqueue(envelope)` alongside `uow.notes`, `uow.tags`), committed in the same transaction. Mirrors the existing `capture` `InMemoryUnitOfWork` pattern. Resolves the gap `hexagonal-arch-shape` explicitly deferred (outbox publish after commit needing a bus or per-handler duplication) — this is the per-handler-duplication path, made cheap by every producing context adding `outbox` to its own UoW protocol.
- **Envelope fields:** `id`, `type: str`, `payload: dict`, `status` (pending/processing/consumed/failed), `attempts: int = 0`, `created_at`, `claimed_at: datetime | None`, `claimed_by: str | None`. Claim fields are part of the schema now so no migration is needed later, but the actual claim/lock *algorithm* (e.g. `SELECT ... FOR UPDATE SKIP LOCKED`) is parked — undecided until `distill` exists as real consumer code and the still-OPEN `single-loop-workers` thread from `overview-thougts` gets resolved.
- **Envelope typing:** `OutboxEnvelope` stays generic (`payload: dict`) — concrete per-`type` payload shapes (e.g. `NoteApprovedPayload`) live in their producing context (`domain/capture/`), serialized to dict at enqueue time. Keeps `domain/shared/outbox` thin rather than collecting every event's schema.
- **First event — `note_approved`:** payload is a **denormalized snapshot**, not id-references — `note_id`, `session_id`, `topic: {id, label}`, `content`, `tags: [{id, label}]`, `approved_at`. Chosen over bare-id references because the outbox's job here is module isolation (note-save shouldn't have to reach into capture's repos to resolve labels) — that's more load-bearing than avoiding payload duplication. Schema drift is handled by minting a new `type` (e.g. `note_approved_v2`) rather than mutating the payload shape under the same `type` in place — mirrors the `CoreException.code()` versioned-string precedent already in the codebase.
- **S-06 implementation target:** in-memory adapter only (`InMemoryFirst` convention) — no real Postgres outbox table yet. `plan.md` for S-06 should scope to `domain/shared/outbox/{model.py,ports.py}` + an in-memory `OutboxRepository` impl + capture's `UnitOfWork` gaining an `outbox` member + the `note_approved` snapshot payload.

**Parked, not decided here:**
- Consumer-side dequeue/claim algorithm (polling shape, locking) — waits for `distill` to actually exist.
- Whether note-save (after its own commit) pushes a second envelope for flashcard-gen (multi-producer outbox) — out of scope for this session.
- Whether `remember` ever touches the outbox, pending the undecided capture/remember module-merge question.
- Delivery semantics (at-least-once implied) and consumer idempotency, esp. for the Notion-backed note-save adapter given `backend-stack`'s already-flagged no-atomic-cross-store-transaction risk.

**Session closed 2026-09-02.** Linked from `context/changes/capture-flow-review-approve-outbox/change.md`'s `## Context`. Next step: `/plan capture-flow-review-approve-outbox` can now draw on the settled shape above; a `hexagonal-arch-shape` ADR amendment for the `domain/shared/` bucket is still owed before or during that plan.

## Log

### 2026-09-02 — bucket-placement: domain/shared (+application/shared) as a general-purpose shared bucket, outbox is its first tenant — ACCEPTED
Why: user wants a home for cross-context abstractions beyond just the outbox (named example: LLM-instruction value objects), so a fourth bounded context (`domain/outbox/`) or per-context duplication were both rejected in favor of extending the directory convention with a real shared layer.
Consequence: `hexagonal-arch-shape`'s directory convention sketch (`domain/<context>/`, `application/<context>/`) needs an amendment once this session's shape is final — it currently has no shared bucket.

### 2026-09-02 — atomicity: outbox enqueue as a member of the producer's own UnitOfWork — ACCEPTED
Why: user picked the transactional-outbox-via-UoW option over a separate post-commit write. Matches the existing `capture` `InMemoryUnitOfWork` shape (per-repo snapshot/restore, one `commit()`), gives atomic outbox+domain-write commits for free from the SQL adapter, and resolves the gap `hexagonal-arch-shape`'s decision doc explicitly deferred ("publishing to the outbox after a successful commit... will need either per-handler duplication or introducing a bus later").
Consequence: `OutboxRepository` is a domain port added to each producing context's own `UnitOfWork` protocol, not a bus and not a standalone post-commit step.

### 2026-09-02 — module-split: three domain modules are capture, distill, remember; distill has two consumer processes (note-save, flashcard-gen) — ACCEPTED
Why: user confirmed the domain split is product-loop-shaped (capture → distill → remember), not process-shaped. `distill` is one domain module realized as two separate outbox-consuming processes filtering by envelope `type`. `remember`'s relationship to capture (possibly one shared conversational handler) is explicitly not yet decided — flagged, not resolved here.
Consequence: envelope `type` values need to distinguish note-save-bound vs. flashcard-gen-bound work within `distill`, not just capture-vs-distill. Whether `remember` ever produces or consumes outbox envelopes is still open.

### 2026-09-02 — bucket-placement: precise path is domain.shared.outbox.model / domain.shared.outbox.ports, ports live alongside the model — ACCEPTED
Why: user refined the earlier bucket-placement decision — `domain/shared/` isn't flat, each shared concern gets its own sub-package (`outbox` first), and the `OutboxRepository` port belongs in that same sub-package next to `OutboxEnvelope`, not in a separate top-level `domain/shared/ports.py`.
Supersedes: 2026-09-02 bucket-placement (ACCEPTED) — same decision, now with an exact module path.

### 2026-09-02 — session-scope: this session settles envelope shape + first event only; consumer dequeue mechanics parked — ACCEPTED
Why: `distill` doesn't exist in code yet, and the user wants S-06 to work in-memory first (`InMemoryFirst` convention) rather than against a real Postgres claim/lock implementation. Deciding the polling/lock algorithm now would be speculative.
Consequence: claim-related fields (`claimed_at`, `claimed_by`) are in the schema for forward compatibility, but the algorithm that populates them is deferred to whenever `distill`'s first real consumer is built.

### 2026-09-02 — envelope-fields: id, type, payload (dict), status, attempts, created_at, claimed_at, claimed_by — ACCEPTED
Why: user picked the full field set in one pass rather than growing it later — explicit status lifecycle (not just a boolean consumed flag) for retry/dead-letter handling, `attempts` to cut off poison messages, and claim fields reserved even though the claiming algorithm itself is parked (see `session-scope`).

### 2026-09-02 — envelope-typing: generic OutboxEnvelope with payload: dict, per-type payload shapes owned by the producing context — ACCEPTED
Why: user confirmed `domain/shared/outbox` should stay thin and generic rather than becoming a registry of every event's schema. A producing context (e.g. `domain/capture/`) defines and serializes its own typed payload (e.g. `NoteApprovedPayload`) before calling `uow.outbox.enqueue(...)`.

### 2026-09-02 — payload-shape: note_approved payload is a denormalized snapshot (labels, not just ids), schema drift handled by minting a new `type` — ACCEPTED
Why: user was initially conflicted (snapshot is easier to consume but harder to keep in sync; id-references are lighter but couple distill to capture's stores at read time and are more fragile to a future DB split). Resolved by treating the outbox as the actual module-isolation boundary — a consumer reaching back into another context's repos defeats that purpose — and by borrowing the `CoreException.code()` precedent (versioned identifier instead of in-place mutation) to keep schema evolution explicit: a changed shape gets a new `type` (e.g. `note_approved_v2`) rather than a silently mutated payload under the same `type`.
Payload: `note_id`, `session_id`, `topic: {id, label}`, `content`, `tags: [{id, label}]`, `approved_at`.

### 2026-09-02 — flashcard-gen-trigger: whether note-save produces a second envelope for flashcard-gen — PARKED
Why: user explicitly deferred this — `distill` doesn't exist yet, and deciding a multi-producer chain now (note-save enqueuing for flashcard-gen after its own commit) is out of scope for a session meant to unblock S-06's producer-only push.

### 2026-09-02 — inmemory-first: S-06 targets an in-memory OutboxRepository only, no real Postgres table yet — ACCEPTED
Why: user wants the outbox to "work in memory" for now, consistent with the project's `InMemoryFirst` layering rule — behavior proven against the in-memory adapter before any SQL adapter is built.
