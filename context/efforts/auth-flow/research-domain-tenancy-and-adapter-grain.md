---
date: 2026-09-13T23:53:00+02:00
topic: "Domain tenancy wiring and adapter-level cross-cutting concerns (remember lock pattern)"
topic_slug: domain-tenancy-and-adapter-grain
container_id: auth-flow
tags: [research, auth, tenancy, remember, hexagonal, compose]
last_updated: 2026-09-13
---

# Research: Domain tenancy wiring and adapter-level cross-cutting concerns (remember lock pattern)

## Research Question

/research auth-flow tożsamość w domenach, gdzie trzeba wpiąć - dodatkowo mamy w adapterze remember lock na cały moduł remember, chce uniknąc takich sytuacji, spróbuj zdefiniuj takie problemy

## Summary

Weles has **no tenancy axis in code today** (`user_id` / owner / principal absent from `backend/src`). FR-005 / PRD FR-008 require **per-person data across the full** capture → distill → remember chain; partial scoping on one port is explicitly worse than none. Identity should enter at the **HTTP input adapter** (fail closed before DB/LLM), flow through **application** command/query handlers as a principal, appear on **domain aggregates** where invariants require it, and be **enforced in every outbound port** that reads or writes person data—not only in compose singletons or one repository.

Remember serializes **all mutations** through a **single global exclusion grain**: Postgres `pg_advisory_xact_lock` with one fixed key, or a shared `asyncio.Lock` in in-memory composition. Queries bypass that grain. Together with **global** `SittingReader.latest()` and **global** `ReviewCatalog`, this encodes single-user-on-instance semantics at the adapter layer. When adding auth, the risk is repeating that pattern—tenancy filters or locks applied at module/compose scope while queries and upstream ports stay global.

This document names **seven problem classes** (anti-patterns) to avoid when wiring auth and when revisiting remember concurrency.

## Findings

### Baseline and effort sequencing

- Frame **FR-05** and PRD **FR-008** require captures, notes, cards, and review history visible only to that person (`context/efforts/auth-flow/frame.md:42`, `context/efforts/auth-flow/prd.md:50–53`).
- **tenancy-reach**: FR-05 spans every capture/distill/remember port and persistence from `db-adapter` (`context/efforts/auth-flow/frame-log.md:7–8`).
- Roadmap **S-01** (sign-in + gate) precedes **S-04** (capture/distill separation) and **S-05** (remember + chain closure) (`context/efforts/auth-flow/roadmap.md:41–99`). Until S-05, remember may still read cross-person data; acceptable only while the hosted instance is not public (`context/efforts/auth-flow/roadmap.md:83–87`).
- Partial `user_id` on remember ports only was rejected: “reads as tenancy while enforcing nothing” (`context/archive/changes/2026-09-10-remember-flow-session-resume/frame-log.md:68–72`).

### Where to wire identity (hexagonal layers)

**HTTP input adapter**

- Routers mount without auth middleware (`backend/src/main.py:36–43`).
- Capture, notes, and remember routes inject commands/queries only—no principal (`backend/src/adapters/http/capture.py`, `notes.py`, `remember.py`).
- MVP ADR already requires an authenticated HTTP API; mechanism deferred (`context/adrs/repo-shape/decision.md:5–6`, `14–16`, `24`).
- FR-006 / FR-009: reject unidentified callers **before** database or LLM work (`context/efforts/auth-flow/frame.md:43`, `prd.md:54–55`).

**Application layer**

- Every HTTP-facing command and query should accept a **principal** (or request-scoped context) and treat cross-tenant resource IDs as not found.
- Today handlers validate existence and domain rules only—for example `GradeCardCommand` loads a sitting by id without an ownership check (`backend/src/application/remember/commands/grade_card.py:44–46`).
- Worker-driven distill commands must still respect ownership via the note/card row stamped at approve time, not via HTTP alone.

**Domain layer**

- No aggregate root carries an owner field today: `CaptureSession` (`backend/src/domain/capture/capture_session.py:27–36`), distill `Note`/`Card`, `Sitting` (`backend/src/domain/remember/sitting.py:28–35`).
- Introduce a stable `UserId` (or equivalent) and `owner_id` on roots where business rules require it: session mint, note/card lineage, sitting uniqueness **per person**.
- `SittingReader.latest()` is defined as the greatest `opened_at` over **all** sittings (`backend/src/domain/remember/ports.py:55–61`)—must become **per-principal** under FR-05.

**Outbound persistence adapters**

- Alembic tables have no tenancy columns (`capture`, `distill`, `remember` migrations under `backend/src/adapters/out/sqlalchemy/migrations/versions/`).
- Highest-leak reads:
  - `SqlAlchemyReviewCatalog.list_reviewable` — all non-discarded distill cards (`backend/src/adapters/out/sqlalchemy/remember/review_catalog.py:15–27`).
  - In-memory catalog via distill `list_all()` (`backend/src/adapters/out/in_memory/remember/review_catalog.py:22–38`).
  - Distill `NoteRepository.list_all` (`backend/src/domain/distill/ports.py:16`; SQL `note_repository.py:52–58`).
  - Capture topic/tag `nearest(embedding)` — global similarity (`backend/src/adapters/out/sqlalchemy/capture/topic_repository.py:40–52`).
  - Remember `SittingRepository.latest()` — unscoped (`backend/src/adapters/out/sqlalchemy/remember/sitting_repository.py:50–57`; used from `open_sitting.py:54`, `due_count.py:38`).

**Composition (`compose.py`)**

- Module-level singletons for tenant-sensitive ports: `_remember_catalog`, `_list_notes_query`, `_get_note_query`, etc. (`backend/src/adapters/compose.py:87–89`, `176–179`).
- FastAPI providers return those singletons; auth will require request-scoped factories or principal arguments on port methods (`compose.py:266–334`).

### Remember lock: mechanism and rationale

**Postgres**

- Each remember command UoW acquires `pg_advisory_xact_lock` with a **single fixed key** `REMEMBER_LOCK_KEY` (`backend/src/adapters/out/sqlalchemy/remember/unit_of_work.py:16–41`).

**In-memory**

- `InMemoryUnitOfWork` acquires an injected `asyncio.Lock` on enter and releases on exit (`backend/src/adapters/out/in_memory/remember/unit_of_work.py:45–62`).
- Tests share one lock per `InMemoryRememberComposition` (`backend/tests/integration/support/in_memory_remember.py:77–116`).

**Compose wiring**

- All remember **commands** share `_remember_unit_of_work` (`backend/src/adapters/compose.py:259–334`).
- Remember **queries** use repository readers directly—**no UoW, no lock** (`backend/src/adapters/compose.py:294–326`).

**Why it exists**

- Overlapping `GradeCardCommand` invocations can double-append events without serializing the read–write window (`context/archive/changes/2026-09-09-remember-flow-review-session/plan.md:127–138`).
- `OpenSittingCommand` races on `latest()` → resume or mint before either transaction commits; per-sitting lock is awkward because open runs **before** a sitting id exists (`plan.md:136–138`; `context/efforts/db-adapter/frame-log.md:98–103`).
- Capture uses **optimistic versioning** per session instead (`backend/src/adapters/out/sqlalchemy/capture/capture_session_repository.py:27–60`); distill UoW has **no** advisory lock.

**Interaction with future auth**

- Global lock + global `latest()` implies **one review stream per instance**, not per person. Multi-user requires partition keys on `latest()`, catalog, scheduling, and likely **finer-grained** concurrency (per owner or per sitting), not a wider mutex.
- Queries outside the lock create **read/write consistency** gaps for TUI polling while mutations hold the advisory lock.

### Named problem classes (what to avoid)

1. **Global module mutex** — One advisory key or one shared `asyncio.Lock` for all mutations in a bounded context, regardless of card, sitting, or (future) `owner_id`. Symptom: unrelated users block each other; auth does not fix throughput without re-keying the lock.

2. **Locked writes, naked reads** — Commands hold the only exclusion; CQRS-lite queries hit repositories without the same boundary. Symptom: read-your-writes and monotonic-read gaps between grade/open and `CurrentCardQuery` / `DueCountQuery`.

3. **Singleton aggregate selection** — APIs like `latest()` with no partition key encode single-tenant semantics in the port contract. Symptom: auth added as a filter in one adapter method while the port signature still implies a global “current sitting.”

4. **Composition-smuggled semantics** — Cross-cutting behavior (lock, tenancy, tracing) hidden in adapter constructors or `compose` wiring, not visible on the application `UnitOfWork` or repository port. Symptom: second cross-cutting concern copied into the same choke point; half the ports never updated.

5. **Choke-point scaling** — Serializing an entire context because one flow lacks an id to lock early (`OpenSitting`), instead of per-aggregate conflicts (DB uniqueness per owner, optimistic version, idempotent commands). Symptom: unnecessary loss of parallelism even for single-user workloads.

6. **Partial tenancy** — Owner id on some tables or ports but global catalog/list/query paths unchanged. Symptom: documented in frame-log as worse than no tenancy; remember `ReviewCatalog` remains the canonical leak.

7. **Process-wide singleton readers** — Tenant-scoped data served from singleton adapters in `compose.py`. Symptom: correct per-request principal at HTTP layer but shared mutable or unfiltered reader state across concurrent requests in one worker.

### Direction for auth-flow slices (non-prescriptive)

- **S-01**: HTTP gate + principal type; no partial port filters without a chain-wide plan.
- **S-04**: Stamp and enforce owner on capture → distill path (notes, cards, outbox handlers, topic/tag decision documented).
- **S-05**: Remember catalog, `latest(principal)`, scheduling/events/card source joins; revisit remember lock grain **with** tenancy (e.g. advisory hash of owner id + uniqueness constraints), not a broader global mutex.
- Prefer the same patterns as capture (optimistic conflict) where remember races are per sitting or per card, rather than expanding adapter-level module locks.

## Code References

- `backend/src/main.py:36–43` — routers mounted without auth
- `backend/src/domain/remember/ports.py:55–61` — global `SittingReader.latest()` contract
- `backend/src/adapters/out/sqlalchemy/remember/unit_of_work.py:16–41` — single `pg_advisory_xact_lock` key for all remember commands
- `backend/src/adapters/out/in_memory/remember/unit_of_work.py:45–62` — shared `asyncio.Lock` on UoW enter/exit
- `backend/src/adapters/compose.py:259–334` — remember commands via shared UoW factory; queries without lock at `294–326`
- `backend/src/adapters/out/sqlalchemy/remember/review_catalog.py:15–27` — global reviewable card query
- `backend/src/adapters/out/sqlalchemy/capture/capture_session_repository.py:27–60` — capture optimistic session conflict (contrast with remember)
- `context/efforts/auth-flow/frame-log.md:7–8` — tenancy-reach across all ports
- `context/archive/changes/2026-09-10-remember-flow-session-resume/frame-log.md:68–72` — partial user_id rejected
- `context/archive/changes/2026-09-09-remember-flow-review-session/plan.md:127–138` — remember lock race rationale

## Open Questions

- Are capture **topic/tag** vocabularies per person or shared on an instance (affects `nearest` and migrations)?
- Outbox worker: is note-level owner sufficient, or should envelopes carry `owner_id` for defense in depth?
- Should remember lock re-graining ship in **S-05** with tenancy, or as a separate change before multi-user traffic on one instance?
